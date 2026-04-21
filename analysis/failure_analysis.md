# Báo cáo Phân tích Thất bại (Failure Analysis Report)

## 1. Tổng quan Benchmark
- **Tổng số cases:** 60
- **Tỉ lệ Pass/Fail:** 54/6
- **Điểm RAGAS trung bình:**
    - Faithfulness: 0.8642
    - Relevancy: 0.8808
    - Retrieval Hit Rate: 0.8500
    - Retrieval MRR: 0.7167
- **Điểm LLM-Judge trung bình:** 4.2667 / 5.0
- **Agreement Rate (Multi-Judge):** 0.925
- **Final Answer Accuracy:** 0.75
- **Hallucination Rate:** 0.10
- **Latency trung bình:** 2.035s / case
- **Tổng Cost ước tính:** 0.0192651 USD

Nhận xét nhanh:
- Chất lượng answer tăng rõ so với baseline trong regression (V1 Score 2.45 -> V2 Score 4.2667).
- Retrieval vẫn là điểm nghẽn chính: Hit Rate 0.85 nhưng MRR chỉ 0.7167 (đúng nhưng chưa lên top-1 đủ nhiều).
- Lỗi tập trung ở câu hỏi mơ hồ yes/no và câu pháp lý dài có nhiều ràng buộc điều kiện.

## 2. Phân nhóm lỗi (Failure Clustering)
| Nhóm lỗi | Số lượng | Nguyên nhân dự kiến |
|----------|----------|---------------------|
| Partial rank miss (not top-1) | 15 | Retriever lấy được đoạn đúng trong top-k nhưng xếp hạng chưa tốt nên MRR giảm |
| Retriever miss (wrong article) | 5 | Query dài/phức hợp làm tín hiệu lexical nhiễu, dẫn đến chọn sai Điều |
| Ambiguous/Yes-No wording | 4 | Dạng câu hỏi "có/không" thiếu anchor Điều/khoản nên dễ lệch retrieval |

## 3. Phân tích 5 Whys (Chọn 3 case tệ nhất)

### Case #1: "Tổ chức bảo hiểm xã hội có nghĩa vụ công khai báo cáo tài chính về Quỹ Bảo hiểm y tế vào thời điểm nào?"
1. **Symptom:** Retrieval `hit_rate=0`, `mrr=0`.
2. **Why 1:** Câu hỏi yêu cầu thông tin "thời điểm" nhưng chunk chứa nội dung này không đứng đầu top-k.
3. **Why 2:** Retrieval hiện dựa nhiều vào overlap token, chưa ưu tiên intent dạng "khi nào/thời điểm".
4. **Why 3:** Không có reranker semantic để đẩy đoạn chứa temporal condition lên top-1.
5. **Why 4:** Chưa có feature extraction cho từ khóa pháp lý thời gian (sau mỗi năm, định kỳ, ngay khi...).
6. **Root Cause:** Ranking chưa theo intent câu hỏi (temporal/condition-based).

### Case #2: "Người có thẻ bảo hiểm y tế có thể khám, chữa bệnh tại cơ sở nào mà không cần đăng ký ban đầu?"
1. **Symptom:** Retrieval `hit_rate=0`, `mrr=0`.
2. **Why 1:** Query diễn đạt phủ định ("không cần đăng ký ban đầu") khó match trực tiếp với cách diễn đạt trong điều luật.
3. **Why 2:** Hệ thống chưa normalize câu hỏi phủ định -> điều kiện đặc biệt/cấp cứu/chuyển tuyến.
4. **Why 3:** Không có bước multi-query decomposition cho câu hỏi nhiều điều kiện đồng thời.
5. **Why 4:** Chunk chứa điều kiện đúng có thể nằm ở vị trí thấp do thiếu clause-level rank boosting.
6. **Root Cause:** Thiếu query rewriting cho câu phủ định và thiếu reranking theo điều kiện pháp lý.

### Case #3: "Tổ chức bảo hiểm xã hội có quyền xử lý người lao động vi phạm Điều lệ Bảo hiểm y tế không?"
1. **Symptom:** Retrieval `hit_rate=0`, trả về sai Điều.
2. **Why 1:** Đây là câu yes/no về thẩm quyền xử lý vi phạm, thông tin thường rải ở chương quyền-trách nhiệm + xử lý vi phạm.
3. **Why 2:** Retriever chưa nối được quan hệ giữa "quyền" và "xử lý vi phạm" qua nhiều Điều.
4. **Why 3:** Chưa có bước graph-like linking giữa các điều có quan hệ nghiệp vụ gần nhau.
5. **Why 4:** Judge LLM yêu cầu độ chính xác ngữ nghĩa cao hơn nên lỗi retrieval lộ rõ hơn trước.
6. **Root Cause:** Thiếu cơ chế multi-hop retrieval cho câu hỏi liên Điều.

## 4. Kế hoạch cải tiến (Action Plan)
- [ ] Thêm query rewriting theo intent (`yes/no`, `thời điểm`, `điều kiện ngoại lệ`) trước bước retrieval.
- [ ] Thêm reranker semantic cho top-10 để cải thiện lỗi `partial rank miss` (mục tiêu tăng MRR lên >= 0.80).
- [ ] Bổ sung multi-query decomposition cho câu hỏi có nhiều điều kiện/phủ định.
- [ ] Tạo map liên kết liên Điều (quyền, nghĩa vụ, xử lý vi phạm) để hỗ trợ multi-hop retrieval.
- [ ] Chạy lại regression trên cùng fixed dataset và theo dõi các delta: HitRate, MRR, Final Answer Accuracy, Cost.
