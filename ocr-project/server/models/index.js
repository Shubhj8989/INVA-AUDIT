const sequelize = require("../config/database");

const Site = require("./Site");
const ItemMaster = require("./ItemMaster");
const ItemMapping = require("./ItemMapping");
const BatchImport = require("./BatchImport");
const OracleSalesRegister = require("./OracleSalesRegister");
const OracleGRNRegister = require("./OracleGRNRegister");
const OracleStockTransfer = require("./OracleStockTransfer");
const PhysicalDocument = require("./PhysicalDocument");
const DocumentPage = require("./DocumentPage");
const ExtractedLineItem = require("./ExtractedLineItem");
const Discrepancy = require("./Discrepancy");
const AuditLog = require("./AuditLog");

// Associations
BatchImport.hasMany(OracleSalesRegister, { foreignKey: "batchId", as: "salesRegisters" });
OracleSalesRegister.belongsTo(BatchImport, { foreignKey: "batchId" });

BatchImport.hasMany(OracleGRNRegister, { foreignKey: "batchId", as: "grnRegisters" });
OracleGRNRegister.belongsTo(BatchImport, { foreignKey: "batchId" });

BatchImport.hasMany(OracleStockTransfer, { foreignKey: "batchId", as: "stockTransfers" });
OracleStockTransfer.belongsTo(BatchImport, { foreignKey: "batchId" });

BatchImport.hasMany(PhysicalDocument, { foreignKey: "batchId", as: "physicalDocuments" });
PhysicalDocument.belongsTo(BatchImport, { foreignKey: "batchId" });

PhysicalDocument.hasMany(DocumentPage, { foreignKey: "documentId", as: "pages" });
DocumentPage.belongsTo(PhysicalDocument, { foreignKey: "documentId" });

PhysicalDocument.hasMany(ExtractedLineItem, { foreignKey: "documentId", as: "lineItems" });
ExtractedLineItem.belongsTo(PhysicalDocument, { foreignKey: "documentId" });

module.exports = {
  sequelize,
  Site,
  ItemMaster,
  ItemMapping,
  BatchImport,
  OracleSalesRegister,
  OracleGRNRegister,
  OracleStockTransfer,
  PhysicalDocument,
  DocumentPage,
  ExtractedLineItem,
  Discrepancy,
  AuditLog,
};
