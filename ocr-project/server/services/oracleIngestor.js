const fs = require("fs");
const path = require("path");
const {
  OracleSalesRegister,
  OracleGRNRegister,
  OracleStockTransfer,
  BatchImport,
  ItemMaster,
} = require("../models");

// Column aliases for resilient auto-mapping
const COLUMN_ALIASES = {
  orderNo: ["order no", "order_no", "sales order", "so number", "order", "sales order no", "order num"],
  invoiceNo: ["invoice no", "invoice_no", "inv no", "gst invoice no", "bill no", "invoice number", "doc no"],
  invoiceDate: ["invoice date", "invoice_date", "inv date", "date", "gst inv date", "bill date", "doc date"],
  customerCode: ["customer code", "cust code", "customer_code", "party code", "account no", "cust no"],
  customerName: ["customer name", "customer", "party name", "buyer name", "bill to name"],
  itemCode: ["item code", "item_code", "product code", "material", "item", "part no", "sku", "code"],
  itemDescription: ["item description", "item desc", "description", "product description", "item name", "desc"],
  quantity: ["quantity", "qty", "billed qty", "invoiced qty", "dispatch qty", "billed quantity", "pcs", "total qty"],
  uom: ["uom", "unit", "unit of measure", "base uom"],
  siteCode: ["site", "site code", "branch", "warehouse", "plant", "location", "sub inventory"],
  lrNo: ["lr no", "lr number", "docket no", "consignment no", "lr_no", "waybill no"],
  transporter: ["transporter", "transporter name", "carrier", "logistics"],
  poNo: ["po no", "po number", "purchase order", "po_no", "order ref"],
  grnNo: ["grn no", "grn number", "mrr no", "receipt no", "grn_no", "goods receipt no"],
  grnDate: ["grn date", "grn_date", "receipt date", "mrr date"],
  vendorCode: ["vendor code", "vendor_code", "supplier code", "supplier no"],
  vendorName: ["vendor name", "vendor", "supplier name", "supplier"],
  transferOrderNo: ["transfer order no", "sto no", "transfer no", "sto number", "transfer order"],
  fromSite: ["from site", "source site", "dispatch location", "from branch"],
  toSite: ["to site", "destination site", "receiving location", "to branch"],
};

function parseCSVLine(line) {
  const result = [];
  let current = "";
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"' || char === "'") {
      inQuotes = !inQuotes;
    } else if (char === "," && !inQuotes) {
      result.push(current.trim().replace(/^["']|["']$/g, ""));
      current = "";
    } else {
      current += char;
    }
  }
  result.push(current.trim().replace(/^["']|["']$/g, ""));
  return result;
}

function parseCSV(content) {
  const lines = content.split(/\r?\n/).filter((l) => l.trim().length > 0);
  if (lines.length < 2) return [];

  const headers = parseCSVLine(lines[0]).map((h) => h.toLowerCase().trim());
  const rows = [];

  for (let i = 1; i < lines.length; i++) {
    const values = parseCSVLine(lines[i]);
    if (values.length === 0 || (values.length === 1 && values[0] === "")) continue;
    const row = {};
    headers.forEach((h, idx) => {
      row[h] = values[idx] || "";
    });
    rows.push(row);
  }
  return rows;
}

function mapRowFields(row, targetType) {
  const mapped = {};
  const rowKeys = Object.keys(row);

  for (const [targetKey, aliases] of Object.entries(COLUMN_ALIASES)) {
    for (const key of rowKeys) {
      const cleanKey = key.toLowerCase().trim().replace(/[_.\-]/g, " ");
      if (aliases.includes(cleanKey) || aliases.includes(key.toLowerCase().trim())) {
        mapped[targetKey] = row[key];
        break;
      }
    }
  }

  // Fallback defaults
  if (!mapped.uom) mapped.uom = "PCS";
  if (!mapped.quantity) {
    // Try to find any numeric column
    for (const k of rowKeys) {
      if (/qty|count|pcs|quantity/i.test(k) && !isNaN(parseFloat(row[k]))) {
        mapped.quantity = parseFloat(row[k]);
        break;
      }
    }
  } else {
    mapped.quantity = parseFloat(String(mapped.quantity).replace(/,/g, "")) || 0;
  }

  return mapped;
}

class OracleIngestor {
  /**
   * Ingests an Oracle Sales Register (CSV/Excel)
   */
  static async ingestSalesRegister(filePath, originalFileName, siteCode = "DEFAULT") {
    const content = fs.readFileSync(filePath, "utf-8");
    const rows = parseCSV(content);

    const batch = await BatchImport.create({
      batchNumber: "BATCH-SALES-" + Date.now(),
      importType: "ORACLE_SALES",
      fileName: originalFileName,
      totalRecords: rows.length,
      status: "PROCESSING",
    });

    const recordsToInsert = [];
    let successCount = 0;
    let failCount = 0;

    for (const row of rows) {
      const mapped = mapRowFields(row, "SALES");
      if (!mapped.itemCode || mapped.quantity === undefined) {
        failCount++;
        continue;
      }

      recordsToInsert.push({
        batchId: batch.id,
        siteCode: mapped.siteCode || siteCode,
        orderNo: mapped.orderNo || null,
        invoiceNo: mapped.invoiceNo || null,
        invoiceDate: mapped.invoiceDate || null,
        customerCode: mapped.customerCode || null,
        customerName: mapped.customerName || null,
        itemCode: String(mapped.itemCode).trim(),
        itemDescription: mapped.itemDescription || "",
        quantity: mapped.quantity,
        uom: mapped.uom || "PCS",
        lrNo: mapped.lrNo || null,
        transporter: mapped.transporter || null,
        rawPayload: JSON.stringify(row),
      });
      successCount++;
    }

    // Bulk insert in chunks of 500
    if (recordsToInsert.length > 0) {
      await OracleSalesRegister.bulkCreate(recordsToInsert);
    }

    await batch.update({
      successfulRecords: successCount,
      failedRecords: failCount,
      status: "COMPLETED",
    });

    return {
      batchId: batch.id,
      batchNumber: batch.batchNumber,
      totalRecords: rows.length,
      successfulRecords: successCount,
      failedRecords: failCount,
    };
  }

  /**
   * Ingests an Oracle GRN Register (CSV/Excel)
   */
  static async ingestGRNRegister(filePath, originalFileName, siteCode = "DEFAULT") {
    const content = fs.readFileSync(filePath, "utf-8");
    const rows = parseCSV(content);

    const batch = await BatchImport.create({
      batchNumber: "BATCH-GRN-" + Date.now(),
      importType: "ORACLE_GRN",
      fileName: originalFileName,
      totalRecords: rows.length,
      status: "PROCESSING",
    });

    const recordsToInsert = [];
    let successCount = 0;
    let failCount = 0;

    for (const row of rows) {
      const mapped = mapRowFields(row, "GRN");
      if (!mapped.itemCode || !mapped.grnNo) {
        failCount++;
        continue;
      }

      recordsToInsert.push({
        batchId: batch.id,
        siteCode: mapped.siteCode || siteCode,
        poNo: mapped.poNo || null,
        grnNo: mapped.grnNo,
        grnDate: mapped.grnDate || null,
        vendorCode: mapped.vendorCode || null,
        vendorName: mapped.vendorName || null,
        itemCode: String(mapped.itemCode).trim(),
        itemDescription: mapped.itemDescription || "",
        quantity: mapped.quantity || 0,
        uom: mapped.uom || "PCS",
        rawPayload: JSON.stringify(row),
      });
      successCount++;
    }

    if (recordsToInsert.length > 0) {
      await OracleGRNRegister.bulkCreate(recordsToInsert);
    }

    await batch.update({
      successfulRecords: successCount,
      failedRecords: failCount,
      status: "COMPLETED",
    });

    return {
      batchId: batch.id,
      batchNumber: batch.batchNumber,
      totalRecords: rows.length,
      successfulRecords: successCount,
      failedRecords: failCount,
    };
  }

  /**
   * Ingests an Oracle Stock Transfer Register (CSV/Excel)
   */
  static async ingestStockTransfers(filePath, originalFileName, defaultSite = "DEFAULT") {
    const content = fs.readFileSync(filePath, "utf-8");
    const rows = parseCSV(content);

    const batch = await BatchImport.create({
      batchNumber: "BATCH-STO-" + Date.now(),
      importType: "ORACLE_TRANSFERS",
      fileName: originalFileName,
      totalRecords: rows.length,
      status: "PROCESSING",
    });

    const recordsToInsert = [];
    let successCount = 0;
    let failCount = 0;

    for (const row of rows) {
      const mapped = mapRowFields(row, "STO");
      if (!mapped.itemCode || !mapped.transferOrderNo) {
        failCount++;
        continue;
      }

      recordsToInsert.push({
        batchId: batch.id,
        transferOrderNo: mapped.transferOrderNo,
        transferDocNo: mapped.invoiceNo || null,
        fromSite: mapped.fromSite || defaultSite,
        toSite: mapped.toSite || "DESTINATION",
        itemCode: String(mapped.itemCode).trim(),
        itemDescription: mapped.itemDescription || "",
        quantity: mapped.quantity || 0,
        uom: mapped.uom || "PCS",
        lrNo: mapped.lrNo || null,
        rawPayload: JSON.stringify(row),
      });
      successCount++;
    }

    if (recordsToInsert.length > 0) {
      await OracleStockTransfer.bulkCreate(recordsToInsert);
    }

    await batch.update({
      successfulRecords: successCount,
      failedRecords: failCount,
      status: "COMPLETED",
    });

    return {
      batchId: batch.id,
      batchNumber: batch.batchNumber,
      totalRecords: rows.length,
      successfulRecords: successCount,
      failedRecords: failCount,
    };
  }
}

module.exports = OracleIngestor;
