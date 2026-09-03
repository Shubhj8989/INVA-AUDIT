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
