const { DataTypes } = require("sequelize");
const sequelize = require("../config/database");

const BatchImport = sequelize.define("BatchImport", {
  id: {
    type: DataTypes.INTEGER,
    autoIncrement: true,
    primaryKey: true,
  },
  batchNumber: {
    type: DataTypes.STRING,
    allowNull: false,
    unique: true,
  },
  importType: {
    type: DataTypes.STRING, // 'ORACLE_SALES', 'ORACLE_GRN', 'ORACLE_TRANSFERS', 'PHYSICAL_SCANS'
    allowNull: false,
  },
  fileName: {
    type: DataTypes.STRING,
    allowNull: true,
  },
  totalRecords: {
    type: DataTypes.INTEGER,
    defaultValue: 0,
  },
  successfulRecords: {
    type: DataTypes.INTEGER,
    defaultValue: 0,
  },
  failedRecords: {
    type: DataTypes.INTEGER,
    defaultValue: 0,
  },
  reviewNeededRecords: {
    type: DataTypes.INTEGER,
    defaultValue: 0,
  },
  status: {
    type: DataTypes.STRING, // 'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED'
    defaultValue: "PENDING",
  },
  metadata: {
    type: DataTypes.TEXT, // JSON string for extra metrics/progress
    allowNull: true,
  },
});

module.exports = BatchImport;
