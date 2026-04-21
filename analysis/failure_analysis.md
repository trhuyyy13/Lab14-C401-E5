# Báo cáo Phân tích Thất bại (Failure Analysis Report)

## 1. Tổng quan Benchmark
- **Tổng số cases:** 50
- **Tỉ lệ Pass/Fail:** 43/7
- **Phân bố theo độ khó:**

| Độ khó | Tổng | Fail | Avg Score |
|--------|------|------|-----------|
| easy | 15 | 0 | 4.57/5 |
| medium | 15 | 0 | 4.78/5 |
| hard | 12 | 3 | 3.92/5 |
| adversarial | 8 | 4 | 3.19/5 |


### Metrics tổng hợp

| Metric | Giá trị |
|--------|---------|
| Retrieval Accuracy | 78.00% |
| Hit Rate | 78.00% |
| Average Hit Rate | 78.00% |
| Average MRR | 0.7000 |
| Final Answer Accuracy | 70.00% |
| Hallucination Rate | 2.00% |
| Average Score (Judge) | 4.25 / 5.0 |
| Agreement Rate (Multi-Judge) | 97.00% |
| User Satisfaction Score | 4.11 / 5.0 |
| Avg Latency | 2.58s / case |
| Cost per Case | $0.000605 |
| Total Cost | $0.0303 |
| Faithfulness (RAGAS) | 0.90 |
| Relevancy (RAGAS) | 0.80 |

## 2. Regression Testing (V1 vs V2)
| Metric | V1 Base | V2 Optimized | Delta |
|--------|---------|--------------|-------|
| Avg Score | 4.32 | 4.25 | -0.06 |
| Hit Rate | 0.78 | 0.78 | +0.00 |
| Hallucination Rate | 4.00% | 2.00% | -2.00% |
| User Satisfaction | 4.20 | 4.11 | -0.09 |
| Avg Latency (s) | 2.96 | 2.58 | -0.38 |
| Cost/Case (USD) | 0.00038 | 0.00060 | +0.00023 |

## 3. Phân nhóm lỗi (Failure Clustering)
| Nhóm lỗi | Số lượng | Nguyên nhân dự kiến |
|----------|----------|---------------------|
| reasoning | 3 | Thiếu khả năng suy luận đa bước |
| prompt-injection | 2 | Agent cần kháng cự yêu cầu tấn công |
| wrong-premise | 1 | Agent phải phát hiện tiền đề sai trong câu hỏi |
| ambiguous | 1 | Agent cần yêu cầu làm rõ thay vì đoán mò |

## 4. Phân tích 5 Whys (3 case tệ nhất)

### Case #1: [hard / reasoning] — Score 1.9/5
**Câu hỏi:** Bà B là công dân Việt Nam, có thẻ bảo hiểm y tế tự nguyện và đang nuôi một trẻ em 5 tuổi. Trong trường hợp bà B mắc bệnh và cần khám chữa bệnh, liệu b...

Symptom: Câu trả lời của AI không cung cấp thông tin chính xác hoặc đầy đủ về quyền lợi bảo hiểm y tế của bà B, dẫn đến điểm đánh giá thấp.

Why 1: Tại sao AI không cung cấp thông tin chính xác hoặc đầy đủ?  
- Vì AI không tìm thấy thông tin liên quan trong tài liệu.

Why 2: Tại sao AI không tìm thấy thông tin trong tài liệu?  
- Vì tài liệu không được tổ chức hoặc phân loại một cách hiệu quả để cho phép AI truy xuất thông tin dễ dàng.

Why 3: Tại sao tài liệu không được tổ chức hoặc phân loại hiệu quả?  
- Vì quy trình chunking (chia nhỏ thông tin) không được thực hiện đúng cách, dẫn đến việc thông tin quan trọng không được lưu trữ hoặc truy xuất.

Why 4: Tại sao quy trình chunking không được thực hiện đúng cách?  
- Vì không có hướng dẫn rõ ràng hoặc tiêu chuẩn nào cho việc chia nhỏ thông tin liên quan đến bảo hiểm y tế trong hệ thống.

Root Cause: Quy trình chunking thông tin không được thực hiện hiệu quả do thiếu hướng dẫn và tiêu chuẩn rõ ràng, dẫn đến việc AI không thể truy xuất thông tin cần thiết để trả lời câu hỏi về quyền lợi bảo hiểm y tế của bà B.

### Case #2: [hard / reasoning] — Score 1.9/5
**Câu hỏi:** Bà B là công dân Việt Nam, hiện đang hưởng lương hưu hàng tháng và đồng thời là người hưởng trợ cấp mất sức lao động. Bà B có nghĩa vụ tham gia bảo hi...

Symptom: Câu trả lời của AI không chính xác và thiếu thông tin cần thiết về nghĩa vụ tham gia bảo hiểm y tế của bà B và cách tính phí bảo hiểm y tế hàng tháng.

Why 1: Tại sao câu trả lời của AI lại không chính xác?  
- Vì AI không tìm thấy thông tin liên quan trong tài liệu.

Why 2: Tại sao AI không tìm thấy thông tin trong tài liệu?  
- Vì quá trình retrieval không hiệu quả, không lấy được thông tin cần thiết từ cơ sở dữ liệu.

Why 3: Tại sao quá trình retrieval lại không hiệu quả?  
- Có thể do chunking không đúng, dẫn đến việc không truy xuất được thông tin liên quan từ văn bản.

Why 4: Tại sao chunking lại không đúng?  
- Có thể do prompt không được thiết kế rõ ràng hoặc không cung cấp đủ ngữ cảnh để AI hiểu và thực hiện retrieval chính xác.

Root Cause: Thiết kế prompt không rõ ràng và không cung cấp đủ ngữ cảnh cho AI, dẫn đến việc chunking và retrieval không hiệu quả, từ đó gây ra câu trả lời không chính xác.

### Case #3: [hard / reasoning] — Score 1.9/5
**Câu hỏi:** Ông B là cán bộ công chức làm việc tại cơ quan A trong 5 năm và được bổ nhiệm giữ chức vụ Trưởng phòng. Sau một thời gian, ông B bị điều chuyển sang c...

Symptom: Câu trả lời của AI không cung cấp thông tin nào liên quan đến câu hỏi về quy trình và điều kiện miễn nhiệm ông B, dẫn đến điểm thấp về độ chính xác và đầy đủ.

Why 1: Tại sao AI không cung cấp thông tin liên quan đến quy trình miễn nhiệm?  
- Vì AI không tìm thấy thông tin trong tài liệu để trả lời câu hỏi.

Why 2: Tại sao AI không tìm thấy thông tin trong tài liệu?  
- Vì tài liệu không được tổ chức hoặc phân loại một cách hợp lý để cho phép AI truy xuất thông tin dễ dàng.

Why 3: Tại sao tài liệu không được tổ chức hoặc phân loại hợp lý?  
- Vì quy trình cập nhật và duy trì tài liệu không được thực hiện thường xuyên hoặc không có tiêu chuẩn rõ ràng.

Why 4: Tại sao quy trình cập nhật và duy trì tài liệu không được thực hiện?  
- Vì thiếu nguồn lực hoặc sự chú ý từ các cán bộ quản lý trong việc đảm bảo tài liệu luôn đầy đủ và chính xác.

Root Cause: Thiếu tổ chức và duy trì tài liệu liên quan đến quy trình miễn nhiệm, dẫn đến việc AI không thể truy xuất thông tin cần thiết để trả lời câu hỏi.

## 5. Kế hoạch cải tiến (Action Plan)
- [ ] **Chunking**: Xem xét giảm size chunk hoặc dùng Semantic Chunking cho các điều luật dài, tránh loãng thông tin.
- [ ] **Retrieval**: Thêm bước Reranking (Cross-Encoder) sau Vector Search để cải thiện MRR.
- [ ] **Prompt**: Cập nhật System Prompt để xử lý rõ hơn các câu hỏi adversarial và out-of-context.
- [ ] **Agent V2**: Tăng top_k=5 và temperature=0 đã giúp một phần; xem xét thêm query expansion.
- [ ] **Cost**: Dùng gpt-4o-mini cho retrieval embedding, chỉ dùng gpt-4o cho judge để giảm ~40% chi phí.
