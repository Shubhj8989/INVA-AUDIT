const express = require("express");
const {
  PhysicalDocument,
  DocumentPage,
  ExtractedLineItem,
  AuditLog,
} = require("../models");

const router = express.Router();

// Get documents pending human review
router.get("/queue", async (req, res) => {
  try {
    const { status, siteCode } = req.query;
    const where = {};
    if (status) where.status = status;
    else where.needsReview = true;
    if (siteCode) where.siteCode = siteCode;

    const documents = await PhysicalDocument.findAll({
      where,
      include: [
        { model: ExtractedLineItem, as: "lineItems" },
        { model: DocumentPage, as: "pages" },
      ],
      order: [["createdAt", "DESC"]],
      limit: 50,
    });

    res.json({ success: true, count: documents.length, documents });
  } catch (error) {
    console.error("Review queue error:", error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Get a single document with pages & line items for review workbench
router.get("/document/:id", async (req, res) => {
  try {
    const { id } = req.params;
    const document = await PhysicalDocument.findByPk(id, {
      include: [
        { model: ExtractedLineItem, as: "lineItems" },
        { model: DocumentPage, as: "pages" },
      ],
    });

    if (!document) {
      return res.status(404).json({ error: "Document not found" });
    }

    res.json({ success: true, document });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Update/correct extracted fields and approve document
router.put("/document/:id", async (req, res) => {
  try {
    const { id } = req.params;
    const { headers, lineItems, reviewerName = "Analyst", markVerified = true } = req.body;

    const document = await PhysicalDocument.findByPk(id);
    if (!document) {
      return res.status(404).json({ error: "Document not found" });
    }

    // Update document headers & status
    if (headers) {
      document.headerData = JSON.stringify(headers);
      if (headers.pick_slip_no) document.keyIdentifier = headers.pick_slip_no;
      else if (headers.gst_invoice_no) document.keyIdentifier = headers.gst_invoice_no;
      else if (headers.order_no) document.keyIdentifier = headers.order_no;
    }

    if (markVerified) {
      document.needsReview = false;
      document.status = "VERIFIED";
      document.verifiedBy = reviewerName;
      document.verifiedAt = new Date();
    }

    await document.save();

    // Update Line Items
    if (Array.isArray(lineItems)) {
      for (const item of lineItems) {
        if (item.id) {
          const dbItem = await ExtractedLineItem.findByPk(item.id);
          if (dbItem) {
            await dbItem.update({
              itemCode: item.itemCode,
              description: item.description,
              quantity: item.quantity,
              uom: item.uom || "PCS",
              needsReview: false,
              isUserModified: true,
            });
          }
        } else {
          // New line item added by user
          await ExtractedLineItem.create({
            documentId: document.id,
            srNo: item.srNo || 1,
            itemCode: item.itemCode,
            description: item.description,
            quantity: item.quantity,
            uom: item.uom || "PCS",
            needsReview: false,
            isUserModified: true,
          });
        }
      }
    }

    // Audit log entry
    await AuditLog.create({
      action: "MANUAL_CORRECTION",
      entityType: "DOCUMENT",
      entityId: document.id,
      performedBy: reviewerName,
      details: JSON.stringify({
        verified: markVerified,
        updatedItemsCount: lineItems?.length || 0,
      }),
    });

    res.json({
      success: true,
      message: "Document reviewed and saved successfully",
      document,
    });
  } catch (error) {
    console.error("Save review error:", error);
    res.status(500).json({ success: false, error: error.message });
  }
});

module.exports = router;
