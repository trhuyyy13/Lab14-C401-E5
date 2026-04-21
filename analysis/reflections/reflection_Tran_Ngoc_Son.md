# Reflection – Lab Day 14: AI Evaluation Factory
**Họ và tên:** Trần Ngọc Sơn  
**Ngày:** 21/04/2026  
**Lab:** Lab 14 – AI Evaluation Factory (Team Edition)

---

## 1. Engineering Contribution — Tôi đã đóng góp gì?

Tôi chịu trách nhiệm chính cho toàn bộ pipeline kỹ thuật trong lab này, bao gồm các module phức tạp nhất:

### Async Pipeline (`engine/runner.py`, `main.py`)
Thiết kế và implement pipeline chạy bất đồng bộ hoàn toàn bằng `asyncio`. `BenchmarkRunner.run_all()` xử lý 50 cases theo batch song song (batch_size=5) để tránh rate limit, mỗi batch gọi `asyncio.gather()` để chạy đồng thời: agent query → RAGAS eval → multi-judge. Toàn bộ V1 + V2 chạy xong trong < 2 phút thay vì ~25 phút nếu chạy tuần tự.

### Multi-Judge Consensus Engine (`engine/llm_judge.py`)
Implement 2 judge độc lập: **GPT-4o** (Judge A) và **GPT-4o-mini** (Judge B), gọi song song bằng `asyncio.gather`. Mỗi judge chấm 3 tiêu chí riêng biệt: accuracy, completeness, professionalism. Logic xử lý conflict tự động:
- Lệch ≤ 1 điểm → agreement_rate = 1.0, lấy trung bình
- Lệch > 1 điểm → conflict = True, dùng GPT-4o làm tiebreaker

### RAG Agent thực tế (`agent/main_agent.py`, `data/ingest.py`)
Thay toàn bộ placeholder bằng RAG thực: ChromaDB + `text-embedding-3-small` cho retrieval, GPT-4o-mini cho generation. Ingest 2 văn bản pháp luật → 125 chunks theo article-based strategy. Agent trả về `retrieved_ids` thực để pipeline tính Retrieval metrics chính xác.

### Extended Metrics (`engine/runner.py`)
Bổ sung 9 metrics mới trên mỗi test case: Hallucination Rate (phát hiện agent trả lời sai khi hit_rate=0), User Satisfaction Score (weighted: `0.5×acc + 0.3×comp + 0.2×prof`), Cost tracking (`tokens_used × $0.30/1M`), Final Answer Accuracy (% cases accuracy ≥ 4/5).

### Golden Dataset & SDG (`data/synthetic_gen.py`)
Implement SDG thực với GPT-4o-mini sinh 42 cases theo 3 mức độ (15 Easy + 15 Medium + 12 Hard) cộng 8 Adversarial hardcoded (prompt injection, out-of-context, sai tiền đề, câu hỏi mơ hồ). Mỗi case có `expected_retrieval_ids` mapping về chunk ID thực trong ChromaDB.

---

### Trade-off Chi phí vs Chất lượng
| Lựa chọn | Chi phí/1M tokens | Chất lượng Judge |
|---|---|---|
| GPT-4o làm cả 2 judge | ~$15 | Cao nhất |
| GPT-4o + GPT-4o-mini (lab này) | ~$8 | Tốt, có conflict detection |
| GPT-4o-mini làm cả 2 | ~$0.60 | Thấp hơn, thiếu diversity |

Kết luận thực tế: dùng GPT-4o làm tiebreaker (chỉ khi conflict) giảm ~45% chi phí judge so với dùng GPT-4o toàn bộ, trong khi vẫn giữ được chất lượng cho 97% cases đồng thuận.

---

## 2. Problem Solving — Các vấn đề phát sinh và cách giải quyết

**Vấn đề 1: ChromaDB lỗi `tenant` khi dùng với asyncio**  
*Triệu chứng:* `ValueError: Could not connect to tenant default_tenant` xảy ra khi `asyncio.to_thread()` gọi `_get_collection()` trong worker thread.  
*Nguyên nhân gốc:* `chromadb.PersistentClient` dùng internal state gắn với thread khởi tạo. Lazy-loading trong worker thread khiến client không tìm được tenant đã init ở main thread.  
*Giải pháp:* Chuyển khởi tạo collection vào `__init__` — luôn chạy ở main thread. Worker thread chỉ gọi `collection.query()` trên object đã sẵn sàng, không tạo mới client.

**Vấn đề 2: `DuplicateIDError` trong ChromaDB khi ingest**  
*Triệu chứng:* `chromadb.errors.DuplicateIDError: found duplicates of: nghi_dinh_bhyt_dieu_2, nghi_dinh_bhyt_dieu_3`.  
*Nguyên nhân gốc:* Nghị định BHYT có cấu trúc lồng nhau — Điều 1-4 của nghị định chính, tiếp theo là Điều lệ đính kèm cũng bắt đầu lại từ Điều 1. Regex `split_by_article()` tách tất cả → trùng ID.  
*Giải pháp:* Dùng `seen_ids: dict` để track số lần xuất hiện của mỗi base ID. Lần đầu → `dieu_2`, lần thứ hai → `dieu_2_2`. Đảm bảo uniqueness mà không mất data.

**Vấn đề 3: Hallucination detection false positive**  
*Triệu chứng:* Agent đôi khi trả lời đúng dù `hit_rate=0` (không tìm được chunk đúng).  
*Nguyên nhân:* LLM có parametric knowledge — GPT-4o-mini đã được train trên dữ liệu pháp luật Việt Nam, có thể trả lời từ bộ nhớ mô hình, không phải từ context.  
*Giải pháp tạm:* Thêm điều kiện `is_refusal` — nếu câu trả lời chứa từ khóa từ chối ("không tìm thấy", "ngoài phạm vi") thì không đánh dấu hallucination. Đây là heuristic, không hoàn hảo — cần faithfulness scoring thực (RAGAS) để phân biệt chính xác hơn.

---

## 4. Nếu có thêm thời gian, tôi sẽ làm gì?

1. **Implement Cohen's Kappa thực**: Thay agreement rate binary bằng Cohen's Kappa, cung cấp con số đáng tin cậy hơn về độ đồng thuận judge. Ngưỡng chấp nhận: κ > 0.7.

2. **Position Bias Test hoàn chỉnh**: Implement `check_position_bias()` — với mỗi case, swap thứ tự context và so sánh điểm. Báo cáo bias index = `|score_AB - score_BA| / max_score`.

3. **Reranking với Cross-Encoder**: Thêm bước rerank top-10 → top-3 sau vector search bằng `cross-encoder/ms-marco-MiniLM-L-6-v2`. Kỳ vọng MRR tăng từ ~0.72 → >0.85, Hallucination Rate giảm.

4. **Faithfulness scoring thực bằng RAGAS**: Thay `faithfulness: 0.9` hardcode bằng RAGAS NLI-based faithfulness — đo xem từng câu trong answer có được support bởi retrieved context không.

5. **Cost optimization A/B test**: So sánh `text-embedding-3-small` vs `text-embedding-3-large` về Hit Rate/MRR và chi phí embedding để tìm điểm tối ưu Pareto cho production.
