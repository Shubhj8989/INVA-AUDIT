const { DataTypes } = require("sequelize");
const sequelize = require("../config/database");

const PhysicalDocument = sequelize.define("PhysicalDocument", {
  id: {
    type: DataTypes.INTEGER,
    autoIncrement: true,
    primaryKey: true,
  },
  batchId: {
    type: DataTypes.INTEGER,
    allowNull: true,
  },
  siteCode: {
    type: DataTypes.STRING,
    allowNull: true,
  },
  docType: {
    type: DataTypes.STRING, // 'TAX_INVOICE', 'PICKING_INSTRUCTION', 'PICK_LIST_REPORT', 'LORRY_RECEIPT', 'UNKNOWN'
    defaultValue: "UNKNOWN",
  },
  fileName: {
    type: DataTypes.STRING,
    allowNull: false,
  },
  filePath: {
    type: DataTypes.STRING,
    allowNull: false,
  },
  keyIdentifier: {
    type: DataTypes.STRING, // e.g. pickSlipNo, gstInvoiceNo, or orderNo
    allowNull: true,
    index: true,
  },
  headerData: {
    type: DataTypes.TEXT, // JSON formatted header fields
    allowNull: true,
  },
  confidenceScore: {
    type: DataTypes.FLOAT,
    defaultValue: 1.0,
  },
  needsReview: {
    type: DataTypes.BOOLEAN,
    defaultValue: false,
  },
  reviewReason: {
    type: DataTypes.STRING,
    allowNull: true,
  },
  status: {
    type: DataTypes.STRING, // 'PENDING', 'PROCESSING', 'EXTRACTED', 'VERIFIED', 'FAILED'
    defaultValue: "PENDING",
  },
  verifiedBy: {
    type: DataTypes.STRING,
    allowNull: true,
  },
  verifiedAt: {
    type: DataTypes.DATE,
    allowNull: true,
  },
});

module.exports = PhysicalDocument;
