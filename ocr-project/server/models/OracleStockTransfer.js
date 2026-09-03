const { DataTypes } = require("sequelize");
const sequelize = require("../config/database");

const OracleStockTransfer = sequelize.define("OracleStockTransfer", {
  id: {
    type: DataTypes.INTEGER,
    autoIncrement: true,
    primaryKey: true,
  },
  batchId: {
    type: DataTypes.INTEGER,
    allowNull: true,
  },
  transferOrderNo: {
    type: DataTypes.STRING,
    allowNull: false,
    index: true,
  },
  transferDocNo: {
    type: DataTypes.STRING,
    allowNull: true,
    index: true,
  },
  fromSite: {
    type: DataTypes.STRING,
    allowNull: false,
  },
  toSite: {
    type: DataTypes.STRING,
    allowNull: false,
  },
  transferDate: {
    type: DataTypes.DATEONLY,
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
  rawPayload: {
    type: DataTypes.TEXT,
    allowNull: true,
  },
});

module.exports = OracleStockTransfer;
