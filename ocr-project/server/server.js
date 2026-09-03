const express = require("express");
const cors = require("cors");
const path = require("path");
require("dotenv").config();

const { sequelize } = require("./models");
const ocrRoutes = require("./routes/ocrRoutes");
const oracleRoutes = require("./routes/oracleRoutes");
const batchRoutes = require("./routes/batchRoutes");
const reviewRoutes = require("./routes/reviewRoutes");

const app = express();

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, "public")));
app.use("/uploads", express.static(path.join(__dirname, "uploads")));

// Mount API Routes
app.use("/api/ocr", ocrRoutes);
app.use("/api/oracle", oracleRoutes);
app.use("/api/batch", batchRoutes);
app.use("/api/review", reviewRoutes);

app.get("/api/status", (req, res) => {
  res.json({
    name: "Inventory Verification & OCR Platform API",
    version: "2.0.0",
    status: "Active",
    modules: ["OCR", "Oracle Register Ingestor", "Batch Pipeline", "Review Queue", "Reconciliation Engine"],
  });
});


const PORT = process.env.PORT || 5000;

async function startServer() {
  try {
    if (sequelize) {
      await sequelize.authenticate();
      console.log("✓ MySQL Database connection established successfully.");
      await sequelize.sync({ alter: true });
      console.log("✓ All database tables synced.");
    }
  } catch (error) {
    console.warn("⚠️ MySQL Database not currently running. Backend running in standalone desktop mode.");
  }

  if (process.env.NODE_ENV !== "test" && !process.env.VERCEL) {
    app.listen(PORT, () => {
      console.log(`🚀 Inventory Verification Backend running on http://localhost:${PORT}`);
    });
  }
}

startServer();

module.exports = app;