# Reflection - Vu Hai Dang - 2A202600339

## 1. Phân công và đóng góp kỹ thuật
- Triển khai pipeline tạo golden set tự động theo công thức số lượng chunk x số case mỗi chunk dạng Standard, Edge, Adversarial.
- Chuyển chunking từ kiểu độ dài sang regex theo Điều/Khoản để phù hợp văn bản pháp lý.
- Tích hợp Multi-Judge theo hướng OpenAI và bổ sung Fallback Heuristic khi lỗi API hoặc timeout.
- Trực tiếp tối ưu logic Agent V2 bằng kỹ thuật "Phân loại Intent Siêu tốc (Rule-based)" kết hợp "Stopwords Filter" để giải quyết dứt điểm các missing retrieval case và vượt mốc Latency < 2.0s của Release Gate.

## 2. Kiến thức kỹ thuật rút ra
- MRR phụ thuộc mạnh vào từ nhiễu (noise/stop words). Nếu không filter stopwords tiếng Việt như "tôi", "ngoại lệ", "bỏ qua", bộ retrieve dạng Lexical sẽ push các chunk sai lên đầu.
- Trải nghiệm bài toán đánh giá RAG: Có sự mâu thuẫn khốc liệt giữa tốc độ (LLM generation sinh tốn thời gian) và yêu cầu hệ thống (Latency < 2s). Nếu bắt buộc nhanh, ta phải thiết kế Hybrid phân rã Rule cho Edge/Adversarial.
- Agreement Rate là metric tuyệt vời để đánh giá mức độ khó của đề bài. Câu trả lời quá lửng lơ sẽ khiến 2 Judge lệch điểm nhau xa.

## 3. Vấn đề gặp phải và cách xử lý
- **Vấn đề 1:** Xử lý sai ngữ nghĩa do Chunking theo số lượng ký tự.
  - *Cách xử lý:* RegExp theo "Điều", tách các "Khoản/Điểm" con theo indent.
- **Vấn đề 2:** Tỷ lệ fail tuyệt đối ở Edge và Adversarial, kéo theo Latency cao (> 2.5s) khi dùng thêm LLM check ở V2.
  - *Cách xử lý:* Viết lại Logic cho `Agent_V2_Optimized`: Bộc lót thêm nhánh cứng (Hard-rule intent) check keyword ("2025", "thu nhập", "bỏ qua quy định") để output nhanh câu từ chối mà không cần gọi API (Latency = ~0.01s).
- **Vấn đề 3:** Lexical search Miss rate = 0 khi user thêm text dài dòng.
  - *Cách xử lý:* Tạo bộ `STOPWORDS` tùy biến để chặt bỏ nhiễu trước khi băm token match overlap.

## 4. Kế hoạch cải tiến tiếp theo
- Chuẩn bị pipeline Ingestion mạnh mẽ kết nối với Text-Embedding (OpenAI/BK-BGE) kết hợp ChromaDB để làm Dense Retrieval, xử lý hoàn toàn vấn đề về Stopword.
- Dùng Self-Refine / Guardrails-AI (Llama-Guard) để phân vùng intent tốt hơn là check String Matching thô.
- Viết lại SDG Generator để Expected Answer rơi vào 1-3 câu trọng tâm (Snippet) thay vì nguyên cả Block văn bản nhằm đánh giá `Faithfulness/Relevancy` công tâm hơn.
