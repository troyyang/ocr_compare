-- Insert sample documents
INSERT INTO documents (
    id, filename, file_type, file_path, file_size, 
    upload_timestamp, status, searchable_content, created_by, updated_by
) VALUES
    -- Completed PDF document
    ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a15', 'annual_report.pdf', 'pdf', 
     '/uploads/annual_report.pdf', 1024000, NOW() - INTERVAL '10 days', 'completed',
     'Annual Financial Report 2023...Full extracted text would appear here...', 'a0eebc99-110b-4ef8-bb6d-6bb9bd380a01', 'a0eebc99-110b-4ef8-bb6d-6bb9bd380a01'),
     
    -- Failed image document
    ('b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a15', 'receipt.jpg', 'image', 
     '/uploads/receipt.jpg', 204800, NOW() - INTERVAL '5 days', 'failed', NULL, 'b0eebc99-110b-4ef8-bb6d-6bb9bd380a02', 'b0eebc99-110b-4ef8-bb6d-6bb9bd380a02'),
     
    -- Pending PDF document
    ('c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a15', 'contract.pdf', 'pdf', 
     '/uploads/contract.pdf', 512000, NOW() - INTERVAL '1 day', 'pending', NULL, 'c0eebc99-110b-4ef8-bb6d-6bb9bd380a03', 'c0eebc99-110b-4ef8-bb6d-6bb9bd380a03');

-- Insert OCR results
INSERT INTO ocr_results (
    id, document_id, engine, extracted_text, confidence_score, processing_time_ms,
    page_metrics, estimated_cost, processed_at, error_message,
    created_by, updated_by
) VALUES
    -- Successful PaddleOCR result (for annual_report.pdf)
    ('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a15', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a15', 
     'paddleocr', 'Annual Financial Report 2023...Full extracted text...', 0.92, 3500,
     '[{"page": 1, "confidence": 0.95, "words": 420}, {"page": 2, "confidence": 0.89, "words": 380}]',
     0.07, NOW() - INTERVAL '9 days 23 hours', NULL,
     'd0eebc99-110b-4ef8-bb6d-6bb9bd380a01', 'd0eebc99-110b-4ef8-bb6d-6bb9bd380a01'),
     
    -- Successful Tesseract result (for annual_report.pdf)
    ('e0eebc99-9c0b-4ef8-bb6d-6bb9bd380a15', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a15', 
     'tesseract', 'Annual Financial Report 2023...Slightly different text extraction...', 0.85, 4200,
     '[{"page": 1, "confidence": 0.87, "words": 410}, {"page": 2, "confidence": 0.83, "words": 370}]',
     NULL, NOW() - INTERVAL '9 days 22 hours', NULL,
     'e0eebc99-110b-4ef8-bb6d-6bb9bd380a01', 'e0eebc99-110b-4ef8-bb6d-6bb9bd380a01'),
     
    -- Failed OCR attempt (for receipt.jpg)
    ('f0eebc99-9c0b-4ef8-bb6d-6bb9bd380a15', 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a15', 
     'easyocr', '', NULL, 1200, NULL, 0.15, NOW() - INTERVAL '4 days 18 hours',
     'Image processing failed: Low resolution',
     'f0eebc99-110b-4ef8-bb6d-6bb9bd380a01', 'f0eebc99-110b-4ef8-bb6d-6bb9bd380a01');