const express = require("express");
const multer = require("multer");
const path = require("path");
const fs = require("fs");
const OracleIngestor = require("../services/oracleIngestor");
const {
  OracleSalesRegister,
  OracleGRNRegister,
  OracleStockTransfer,
  BatchImport,
} = require("../models");

const router = express.Router();
const upload = multer({ dest: "uploads/" });

// Upload Oracle Sales Register
router.post("/upload-sales", upload.single("file"), async (req, res) => {
  try {
    if (!req.file) return res.status(400).json({ error: "No file provided" });
    const siteCode = req.body.siteCode || "DEFAULT";

    const result = await OracleIngestor.ingestSalesRegister(
      req.file.path,
      req.file.originalname,
      siteCode
    );

    res.json({
      success: true,
      message: "Oracle Sales Register ingested successfully",
      data: result,
    });
  } catch (error) {
    console.error("Sales ingest error:", error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Upload Oracle GRN Register
router.post("/upload-grn", upload.single("file"), async (req, res) => {
  try {
    if (!req.file) return res.status(400).json({ error: "No file provided" });
    const siteCode = req.body.siteCode || "DEFAULT";

    const result = await OracleIngestor.ingestGRNRegister(
      req.file.path,
      req.file.originalname,
      siteCode
    );

    res.json({
      success: true,
      message: "Oracle GRN Register ingested successfully",
      data: result,
    });
  } catch (error) {
    console.error("GRN ingest error:", error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Upload Oracle Stock Transfers
router.post("/upload-transfers", upload.single("file"), async (req, res) => {
  try {
    if (!req.file) return res.status(400).json({ error: "No file provided" });
    const siteCode = req.body.siteCode || "DEFAULT";

    const result = await OracleIngestor.ingestStockTransfers(
      req.file.path,
      req.file.originalname,
      siteCode
    );

    res.json({
      success: true,
      message: "Oracle Stock Transfers ingested successfully",
      data: result,
    });
  } catch (error) {
    console.error("Stock Transfer ingest error:", error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Get Summary Statistics of Oracle Registers
router.get("/summary", async (req, res) => {
  try {
    const salesCount = await OracleSalesRegister.count();
    const grnCount = await OracleGRNRegister.count();
    const stoCount = await OracleStockTransfer.count();
    const batches = await BatchImport.findAll({
      order: [["createdAt", "DESC"]],
      limit: 10,
    });

    res.json({
      success: true,
      summary: {
        totalSalesRecords: salesCount,
        totalGRNRecords: grnCount,
        totalStockTransferRecords: stoCount,
        recentBatches: batches,
      },
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

module.exports = router;
