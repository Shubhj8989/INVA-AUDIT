const { DataTypes } = require("sequelize");
const sequelize = require("../config/database");

const Discrepancy = sequelize.define("Discrepancy", {
  id: {
    type: DataTypes.INTEGER,
    autoIncrement: true,
    primaryKey: true,
  },
  siteCode: {
    type: DataTypes.STRING,
    allowNull: true,
    index: true,
  },
  verificationType: {
    type: DataTypes.STRING, // 'OUTWARD_SALES', 'INWARD_GRN', 'STOCK_TRANSFER'
    allowNull: false,
    index: true,
  },
  discrepancyType: {
    type: DataTypes.STRING, // 'MATCHED', 'QUANTITY_MISMATCH', 'ITEM_CODE_MISMATCH', 'MISSING_IN_ORACLE', 'MISSING_IN_PHYSICAL', 'MISSING_LR', 'GRN_MISSING', 'INVOICE_MISSING'
    allowNull: false,
    index: true,
  },
  itemCode: {
    type: DataTypes.STRING,
    allowNull: false,
    index: true,
  },
  itemDescription: {
    type: DataTypes.TEXT,
    allowNull: true,
  },
  oracleQty: {
    type: DataTypes.FLOAT,
    defaultValue: 0,
  },
  physicalQty: {
    type: DataTypes.FLOAT,
    defaultValue: 0,
  },
  varianceQty: {
    type: DataTypes.FLOAT,
    defaultValue: 0,
  },
  uom: {
    type: DataTypes.STRING,
    defaultValue: "PCS",
  },
  docReferences: {
    type: DataTypes.TEXT, // JSON with orderNo, invoiceNo, pickSlipNo, grnNo, lrNo
    allowNull: true,
  },
  status: {
    type: DataTypes.STRING, // 'OPEN', 'UNDER_REVIEW', 'RESOLVED'
    defaultValue: "OPEN",
    index: true,
  },
  analystNotes: {
    type: DataTypes.TEXT,
    allowNull: true,
  },
  resolvedBy: {
    type: DataTypes.STRING,
    allowNull: true,
  },
  resolvedAt: {
    type: DataTypes.DATE,
    allowNull: true,
  },
});

module.exports = Discrepancy;
