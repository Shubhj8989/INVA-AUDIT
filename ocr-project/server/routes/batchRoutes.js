const express = require("express");
const multer = require("multer");
const path = require("path");
const BatchProcessor = require("../services/batchProcessor");
const { BatchImport, PhysicalDocument } = require("../models");

const router = express.Router();
const upload = multer({ dest: "uploads/" });

// Bulk upload images
router.post("/upload-bulk", upload.array("files", 100), async (req, res) => {
  try {
    if (!req.files || req.files.length === 0) {
      return res.status(400).json({ error: "No files uploaded" });
    }

    const filePaths = req.files.map((f) => f.path);
    const originalNames = req.files.map((f) => f.originalname);
    const siteCode = req.body.siteCode || "DEFAULT";

    const job = await BatchProcessor.startBatch(filePaths, originalNames, siteCode);

    res.json({
      success: true,
      message: `Batch job ${job.batchNumber} initiated with ${filePaths.length} documents`,
      data: job,
    });
  } catch (error) {
    console.error("Batch upload error:", error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Scan & Ingest direct local directory (designed for 3 Lakh+ images)
router.post("/scan-directory", async (req, res) => {
  try {
    const { directoryPath, siteCode = "SITE-DEFAULT", concurrency = 4 } = req.body;
    if (!directoryPath) {
      return res.status(400).json({ success: false, error: "directoryPath is required" });
    }

    const job = await BatchProcessor.startDirectoryScan(directoryPath, siteCode, concurrency);
    res.json({
      success: true,
      message: `Scanning initiated for ${job.totalFiles} documents from ${directoryPath}`,
      data: job,
    });
  } catch (error) {
    console.error("Directory scan error:", error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Get streaming documents from active batch
router.get("/live-docs/:batchId", (req, res) => {
  const { batchId } = req.params;
  const offset = parseInt(req.query.offset || "0", 10);
  const status = BatchProcessor.getBatchStatus(batchId);
  if (!status) {
    return res.status(404).json({ success: false, error: "Batch not found or not active" });
  }

  const docs = status.documents.slice(offset);
  res.json({
    success: true,
    batchId,
    total: status.totalFiles,
    processed: status.processed,
    docs,
    nextOffset: offset + docs.length,
    isCompleted: status.status === "COMPLETED",
  });
});

// Get live status of a batch job
router.get("/status/:batchId", async (req, res) => {
  try {
    const { batchId } = req.params;
    const liveStatus = BatchProcessor.getBatchStatus(batchId);

    if (liveStatus) {
      return res.json({ success: true, status: liveStatus });
    }

    // Fallback to database record if completed earlier
    const dbBatch = await BatchImport.findByPk(batchId);
    if (!dbBatch) {
      return res.status(404).json({ error: "Batch not found" });
    }

    res.json({
      success: true,
      status: {
        batchId: dbBatch.id,
        batchNumber: dbBatch.batchNumber,
        totalFiles: dbBatch.totalRecords,
        processed: dbBatch.totalRecords,
        successful: dbBatch.successfulRecords,
        failed: dbBatch.failedRecords,
        reviewNeeded: dbBatch.reviewNeededRecords,
        status: dbBatch.status,
        progressPercent: 100,
      },
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// List all physical document batches
router.get("/history", async (req, res) => {
  try {
    const batches = await BatchImport.findAll({
      where: { importType: "PHYSICAL_SCANS" },
      order: [["createdAt", "DESC"]],
      limit: 20,
    });
    res.json({ success: true, batches });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

module.exports = router;
