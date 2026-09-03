const { DataTypes } = require("sequelize");
const sequelize = require("../config/database");

const OracleGRNRegister = sequelize.define("OracleGRNRegister", {
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
  poNo: {
    type: DataTypes.STRING,
    allowNull: true,
    index: true,
  },
  grnNo: {
    type: DataTypes.STRING,
    allowNull: false,
    index: true,
  },
  grnDate: {
    type: DataTypes.DATEONLY,
    allowNull: true,
  },
  vendorCode: {
    type: DataTypes.STRING,
    allowNull: true,
  },
  vendorName: {
    type: DataTypes.STRING,
    allowNull: true,
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
  quantity: {
    type: DataTypes.FLOAT,
    allowNull: false,
  },
  uom: {
    type: DataTypes.STRING,
    defaultValue: "PCS",
  },
  rawPayload: {
    type: DataTypes.TEXT,
    allowNull: true,
  },
});

module.exports = OracleGRNRegister;
