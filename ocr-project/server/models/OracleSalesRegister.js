const { DataTypes } = require("sequelize");
const sequelize = require("../config/database");

const OracleSalesRegister = sequelize.define("OracleSalesRegister", {
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
  orderNo: {
    type: DataTypes.STRING,
    allowNull: true,
    index: true,
  },
  invoiceNo: {
    type: DataTypes.STRING,
    allowNull: true,
    index: true,
  },
  invoiceDate: {
    type: DataTypes.DATEONLY,
    allowNull: true,
  },
  customerCode: {
    type: DataTypes.STRING,
    allowNull: true,
  },
  customerName: {
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
  lrNo: {
    type: DataTypes.STRING,
    allowNull: true,
  },
  transporter: {
    type: DataTypes.STRING,
    allowNull: true,
  },
  rawPayload: {
    type: DataTypes.TEXT,
    allowNull: true,
  },
});

module.exports = OracleSalesRegister;
