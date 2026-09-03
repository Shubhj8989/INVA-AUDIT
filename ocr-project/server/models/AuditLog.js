const { DataTypes } = require("sequelize");
const sequelize = require("../config/database");

const AuditLog = sequelize.define("AuditLog", {
  id: {
    type: DataTypes.INTEGER,
    autoIncrement: true,
    primaryKey: true,
  },
  action: {
    type: DataTypes.STRING, // 'IMPORT', 'OCR_EXTRACT', 'MANUAL_CORRECTION', 'RESOLVE_DISCREPANCY', 'REVERT'
    allowNull: false,
  },
  entityType: {
    type: DataTypes.STRING, // 'DOCUMENT', 'LINE_ITEM', 'DISCREPANCY', 'BATCH'
    allowNull: false,
  },
  entityId: {
    type: DataTypes.INTEGER,
    allowNull: true,
  },
  performedBy: {
    type: DataTypes.STRING,
    defaultValue: "Analyst",
  },
  details: {
    type: DataTypes.TEXT, // JSON details of change (before/after)
    allowNull: true,
  },
});

module.exports = AuditLog;
