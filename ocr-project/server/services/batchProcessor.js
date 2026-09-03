const axios = require("axios");
const fs = require("fs");
const path = require("path");
const FormData = require("form-data");
const {
  BatchImport,
  PhysicalDocument,
  DocumentPage,
  ExtractedLineItem,
} = require("../models");

// In-memory active batch trackers
const activeBatches = new Map();

// Helper to recursively collect all image/pdf files from a directory
function collectFilesRecursively(dir, fileList = []) {
  if (!fs.existsSync(dir)) return fileList;
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const validExts = new Set([".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".pdf"]);

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    try {
      if (entry.isDirectory()) {
        collectFilesRecursively(fullPath, fileList);
      } else if (entry.isFile()) {
        const ext = path.extname(entry.name).toLowerCase();
        if (validExts.has(ext)) {
          fileList.push(fullPath);
        }
      }
    } catch (e) {
      console.warn("Skip inaccessible file/dir:", fullPath);
    }
  }
  return fileList;
}

class BatchProcessor {
  /**
   * Starts a batch job directly from a local directory path on the machine (ideal for 3 Lakh+ images).
   */
  static async startDirectoryScan(dirPath, siteCode = "SITE-DEFAULT", concurrency = 4) {
    if (!fs.existsSync(dirPath)) {
      throw new Error(`Directory does not exist: ${dirPath}`);
    }

    const files = collectFilesRecursively(dirPath);
    if (files.length === 0) {
      throw new Error(`No supported document images (.jpg, .png, .tiff, .pdf) found in: ${dirPath}`);
    }

    const originalNames = files.map(f => path.basename(f));
    return this.startBatch(files, originalNames, siteCode, concurrency);
  }

  /**
   * Initializes a batch job and runs extraction asynchronously with concurrency.
   */
  static async startBatch(files, originalNames = [], siteCode = "DEFAULT", concurrency = 4) {
    const batchNumber = "BATCH-OCR-" + Date.now();
    let batchId = Date.now();

    try {
      if (BatchImport) {
        const batch = await BatchImport.create({
          batchNumber,
          importType: "PHYSICAL_SCANS",
          totalRecords: files.length,
          status: "PROCESSING",
        });
        batchId = batch.id;
      }
    } catch (e) {
      console.warn("Running in standalone batch mode without DB table lock");
    }

    const batchState = {
      batchId,
      batchNumber,
      siteCode,
      totalFiles: files.length,
      processed: 0,
      successful: 0,
      reviewNeeded: 0,
      failed: 0,
      startTime: Date.now(),
      status: "PROCESSING",
      documents: [],
      concurrency: Math.min(Math.max(1, concurrency), 12),
    };

    activeBatches.set(batchId, batchState);

    // Launch concurrent processing asynchronously
    setImmediate(() => {
      this._processQueueConcurrent(batchId, files, originalNames, siteCode);
    });

    return {
      batchId,
      batchNumber,
      siteCode,
      totalFiles: files.length,
      status: "PROCESSING",
    };
  }

  static async _processQueueConcurrent(batchId, files, originalNames, siteCode) {
    const state = activeBatches.get(batchId);
    if (!state) return;

    const concurrency = state.concurrency || 4;
    let currentIndex = 0;

    async function worker() {
      while (currentIndex < files.length) {
        const i = currentIndex++;
        const filePath = files[i];
        const fileName = originalNames[i] || path.basename(filePath);

        try {
          const formData = new FormData();
          formData.append("image", fs.createReadStream(filePath));

          const response = await axios.post("http://127.0.0.1:5001/process", formData, {
            headers: formData.getHeaders(),
            timeout: 60000,
          });

          const data = response.data;
          const struct = data.structured_document || {};
          const classification = data.classification || {};
          const docType = struct.doc_type || classification.doc_type || "UNKNOWN";
          const headers = struct.headers || {};
          const lineItems = struct.line_items || [];
          const hasReviewFlags = struct.has_review_flags || false;

          let keyIdentifier = "";
          if (headers.pick_slip_no?.value) keyIdentifier = headers.pick_slip_no.value;
          else if (headers.gst_invoice_no?.value) keyIdentifier = headers.gst_invoice_no.value;
          else if (headers.order_no?.value) keyIdentifier = headers.order_no.value;
          else if (headers.sales_order_no?.value) keyIdentifier = headers.sales_order_no.value;
          else if (headers.delivery_no?.value) keyIdentifier = headers.delivery_no.value;

          const docRecord = {
            id: Date.now() + i,
            fileName,
            filePath,
            docType,
            keyIdentifier,
            confidence: classification.confidence || 0.9,
            needsReview: hasReviewFlags || !keyIdentifier || lineItems.length === 0,
            reviewReason: hasReviewFlags ? "Confidence warning or missing mandatory identifiers" : "",
            headers: Object.fromEntries(
              Object.entries(headers).map(([k, v]) => [k, v?.value !== undefined ? v.value : v])
            ),
            lineItems: lineItems.map((item, idx) => ({
              id: Date.now() + idx,
              srNo: item.sr_no || idx + 1,
              itemCode: item.item_code || "",
              description: item.description || "",
              quantity: item.qty || item.picked_qty || item.received_qty || 0,
              uom: item.uom || "PCS",
              hsn_code: item.hsn_code || "",
            })),
          };

          state.processed++;
          if (docRecord.needsReview) {
            state.reviewNeeded++;
          } else {
            state.successful++;
          }

          state.documents.push(docRecord);
        } catch (err) {
          state.processed++;
          state.failed++;
          state.documents.push({
            id: Date.now() + i,
            fileName,
            filePath,
            docType: "UNKNOWN",
            confidence: 0,
            needsReview: true,
            reviewReason: `OCR Processing failed: ${err.message}`,
            headers: {},
            lineItems: [],
          });
        }
      }
    }

    // Run parallel workers
    const workers = Array.from({ length: concurrency }, () => worker());
    await Promise.all(workers);

    state.status = "COMPLETED";
    console.log(`[BatchProcessor] Batch ${batchId} finished: ${state.processed}/${state.totalFiles} files processed.`);
  }

  /**
   * Retrieves batch status and live metrics.
   */
  static getBatchStatus(batchId) {
    const live = activeBatches.get(Number(batchId));
    if (live) {
      const elapsedSec = (Date.now() - live.startTime) / 1000;
      const speed = elapsedSec > 0 ? (live.processed / elapsedSec).toFixed(2) : 0;
      const remaining = live.totalFiles - live.processed;
      const etaSeconds = speed > 0 ? Math.round(remaining / speed) : 0;

      return {
        ...live,
        speedDocsPerSec: parseFloat(speed),
        etaSeconds,
        progressPercent: Math.round((live.processed / live.totalFiles) * 100),
      };
    }
    return null;
  }
}

module.exports = BatchProcessor;
