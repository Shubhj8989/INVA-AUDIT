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

class BatchProcessor {
  /**
   * Initializes a batch job and runs extraction asynchronously.
   */
  static async startBatch(files, originalNames = [], siteCode = "DEFAULT") {
    const batchNumber = "BATCH-OCR-" + Date.now();
    const batch = await BatchImport.create({
      batchNumber,
      importType: "PHYSICAL_SCANS",
      totalRecords: files.length,
      status: "PROCESSING",
    });

    const batchState = {
      batchId: batch.id,
      batchNumber,
      totalFiles: files.length,
      processed: 0,
      successful: 0,
      reviewNeeded: 0,
      failed: 0,
      startTime: Date.now(),
      status: "PROCESSING",
      documents: [],
    };

    activeBatches.set(batch.id, batchState);

    // Launch processing asynchronously
    setImmediate(() => {
      this._processQueue(batch.id, files, originalNames, siteCode);
    });

    return {
      batchId: batch.id,
      batchNumber,
      totalFiles: files.length,
      status: "PROCESSING",
    };
  }

  static async _processQueue(batchId, files, originalNames, siteCode) {
    const state = activeBatches.get(batchId);
    if (!state) return;

    for (let i = 0; i < files.length; i++) {
      const filePath = files[i];
      const fileName = originalNames[i] || path.basename(filePath);

      try {
        // Send image to Python OCR & Zonal Service
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

        // Key identifier for cross-linkage
        let keyIdentifier = "";
        if (headers.pick_slip_no?.value) keyIdentifier = headers.pick_slip_no.value;
        else if (headers.gst_invoice_no?.value) keyIdentifier = headers.gst_invoice_no.value;
        else if (headers.order_no?.value) keyIdentifier = headers.order_no.value;
        else if (headers.delivery_no?.value) keyIdentifier = headers.delivery_no.value;

        // Create PhysicalDocument
        const physDoc = await PhysicalDocument.create({
          batchId,
          siteCode,
          docType,
          fileName,
          filePath,
          keyIdentifier,
          headerData: JSON.stringify(headers),
          confidenceScore: classification.confidence || 0.9,
          needsReview: hasReviewFlags || !keyIdentifier || lineItems.length === 0,
          reviewReason: hasReviewFlags ? "Low confidence or missing critical headers" : null,
          status: hasReviewFlags ? "PENDING" : "EXTRACTED",
        });

        // Create DocumentPage
        await DocumentPage.create({
          documentId: physDoc.id,
          pageNumber: 1,
          totalPages: 1,
          imagePath: filePath,
          rawOcrJson: JSON.stringify(data.ocr || {}),
        });

        // Create ExtractedLineItems
        for (const item of lineItems) {
          await ExtractedLineItem.create({
            documentId: physDoc.id,
            srNo: item.sr_no || 1,
            itemCode: item.item_code || "UNKNOWN",
            description: item.description || "",
            quantity: item.qty || 0,
            uom: item.uom || "PCS",
            hsnCode: item.hsn_code || "",
            confidence: item.confidence || 0.9,
            needsReview: item.needs_review || false,
            reviewReason: item.review_reason || null,
          });
        }

        state.processed++;
        if (physDoc.needsReview) {
          state.reviewNeeded++;
        } else {
          state.successful++;
        }

        state.documents.push({
          id: physDoc.id,
          fileName,
          docType,
          keyIdentifier,
          itemsCount: lineItems.length,
          needsReview: physDoc.needsReview,
        });
      } catch (err) {
        console.error(`Batch processing error on ${fileName}:`, err.message);
        state.processed++;
        state.failed++;

        await PhysicalDocument.create({
          batchId,
          siteCode,
          docType: "UNKNOWN",
          fileName,
          filePath,
          confidenceScore: 0,
          needsReview: true,
          reviewReason: `OCR Processing failed: ${err.message}`,
          status: "FAILED",
        });
      }
    }

    state.status = "COMPLETED";

    // Update database batch record
    await BatchImport.update(
      {
        successfulRecords: state.successful,
        failedRecords: state.failed,
        reviewNeededRecords: state.reviewNeeded,
        status: "COMPLETED",
        metadata: JSON.stringify({
          durationMs: Date.now() - state.startTime,
          avgSpeed: (state.processed / ((Date.now() - state.startTime) / 1000)).toFixed(2),
        }),
      },
      { where: { id: batchId } }
    );
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
