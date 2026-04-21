# Báo cáo Phân tích Thất bại (Failure Analysis Report)

## 1. Tổng quan Benchmark
- **Tổng số cases:** 80
- **Tỉ lệ Pass/Fail:** 78/2 (97.5% Pass)
- **Điểm RAGAS trung bình:**
    - Faithfulness: 0.883
    - Relevancy: 0.803
- **Điểm LLM-Judge trung bình:** 4.10 / 5.0
- **Final Answer Accuracy:** 77.6% (Độ chính xác nội dung)
- **Hallucination Rate:** 11.7% (Tỉ lệ bịa đặt/không bám context)
- **Retrieval:** Accuracy = 97.5%, Hit Rate = 0.975, MRR = 0.975
- **Multi-Judge Agreement:** 0.930
- **Hiệu năng:** Avg latency = 0.073s/case, Cost/eval = 0.000113 USD
- **User Satisfaction Score:** 85.6% (Điểm hài lòng người dùng)
- **Trạng thái AI Judge:** OpenAI Judge đang hoạt động (`using_openai = true`).

## 2. Phân nhóm lỗi (Failure Clustering)
| Nhóm lỗi | Số lượng | Nguyên nhân dự kiến |
|----------|----------|---------------------|
| Retrieval Miss | 2 | Một số hard case nhiều ngữ cảnh cạnh tranh làm lệch top-1/top-3 |
| Relevancy thấp (< 0.90) | 59 | Câu trả lời thiên về mẫu trích dẫn chung, chưa phản hồi đúng intent hard cases |
| Faithfulness thấp (< 0.95) | 36 | Khi gặp case mâu thuẫn hoặc đa bước, câu trả lời thiếu căn cứ trích dẫn rõ ràng |
| Prompt Injection / Goal Hijacking | 8 | Agent giữ an toàn nhưng nội dung phản biện còn ngắn, chưa giải thích đầy đủ |
| Conflicting Information | 4 | Chưa có chiến lược đối chiếu 2 nguồn nên điểm relevancy/faithfulness rất thấp |

## 3. Phân tích 5 Whys (Chọn 3 case tệ nhất)

### Case #1: Conflicting info giữa Điều 13 và Điều 14
1. **Symptom:** Relevancy thấp nhất (0.029), faithfulness 0.129 dù vẫn pass theo ngưỡng judge.
2. **Why 1:** Câu hỏi yêu cầu so sánh/ưu tiên diễn giải giữa 2 nguồn, nhưng agent chỉ trả lời theo template một nguồn.
3. **Why 2:** Retriever trả về tài liệu đúng chủ đề nhưng generation không có bước đối chiếu hai đoạn context.
4. **Why 3:** Prompt generation hiện chưa có quy tắc "nêu nguồn A/B và tiêu chí ưu tiên".
5. **Why 4:** Không có bộ kiểm tra hậu kỳ cho câu hỏi dạng conflicting_information.
6. **Root Cause:** Thiếu luồng suy luận chuyên biệt cho câu hỏi đa nguồn và mâu thuẫn thông tin.

### Case #2: Conflicting info giữa Điều 14 và Điều 15
1. **Symptom:** Relevancy 0.057, faithfulness 0.157, chất lượng thấp ở nhóm edge-case.
2. **Why 1:** Agent không trích dẫn rõ từng điều khoản khi phải tổng hợp nhiều nguồn.
3. **Why 2:** Context kết hợp dài, chưa có bước lọc key points theo từng source_id.
4. **Why 3:** Cơ chế trả lời tối ưu tốc độ ưu tiên đoạn đầu thay vì lập luận đầy đủ.
5. **Why 4:** Chưa triển khai reranking theo câu hỏi "so sánh".
6. **Root Cause:** Pipeline chưa có strategy cho câu hỏi cần tổng hợp nhiều mảnh chứng cứ.

### Case #3: Conflicting info giữa Điều 15 và Điều 16
1. **Symptom:** Relevancy 0.086, faithfulness 0.186, không đáp ứng intent "ưu tiên diễn giải".
2. **Why 1:** Agent mới xử lý tốt câu hỏi fact/summary đơn nguồn, chưa vững với câu hỏi reasoning đa nguồn.
3. **Why 2:** Thiếu prompt hướng dẫn cấu trúc trả lời: nêu điểm giống, khác, và kết luận ưu tiên.
4. **Why 3:** Bộ hard cases vừa mở rộng, nhưng logic trả lời chưa được tune tương ứng.
5. **Why 4:** Chưa có regression riêng cho từng category hard case.
6. **Root Cause:** Mở rộng dataset nhanh hơn tốc độ hoàn thiện policy generation theo loại câu hỏi.

## 4. Kế hoạch cải tiến (Action Plan)
- [x] Chuẩn hóa golden set 80 cases có `expected_retrieval_ids` và hard-case categories.
- [x] Tối ưu retrieval ưu tiên match trực tiếp `source_id` trong câu hỏi.
- [x] Bổ sung Multi-Judge OpenAI consensus và conflict resolution.
- [x] Mở rộng hard cases theo guide: adversarial, edge-case, multi-turn, technical.
- [ ] Thêm generator câu trả lời theo `metadata.type` và `hard_case_category`.
- [ ] Thêm policy trả lời chuyên biệt cho `conflicting_information` với so sánh nguồn A/B.
- [ ] Tạo dashboard theo dõi theo category để phát hiện nhóm suy giảm sớm.
- [ ] Tối ưu chi phí 20-30% bằng cache retrieval + nén context có điều kiện.
