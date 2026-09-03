const { DataTypes } = require("sequelize");
const sequelize = require("../config/database");

const ExtractedLineItem = sequelize.define("ExtractedLineItem", {
  id: {
    type: DataTypes.INTEGER,
    autoIncrement: true,
    primaryKey: true,
  },
  documentId: {
    type: DataTypes.INTEGER,
    allowNull: false,
    index: true,
  },
  srNo: {
    type: DataTypes.INTEGER,
    defaultValue: 1,
  },
  itemCode: {
    type: DataTypes.STRING,
    allowNull: false,
    index: true,
  },
  description: {
    type: DataTypes.TEXT,
    allowNull: true,
  },
  quantity: {
    type: DataTypes.FLOAT,
    allowNull: false,
  },
  uom: {
    type: DataTypes.STRING,
    defaultValue: "PCS",
  },
  hsnCode: {
    type: DataTypes.STRING,
    allowNull: true,
  },
  confidence: {
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
  isUserModified: {
    type: DataTypes.BOOLEAN,
    defaultValue: false,
  },
  originalValues: {
    type: DataTypes.TEXT, // JSON of original OCR values before user correction
    allowNull: true,
  },
});

module.exports = ExtractedLineItem;
