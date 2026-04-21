# Reflection - Luo Anh Tuan

## 1. Phan cong va dong gop ky thuat
- Tham gia refactor cac module quan trong de code gon hon va de mo rong: tach helper cho benchmark summary, fallback payload khi test case loi, va helper cho judge heuristic.
- Dong bo luong du lieu theo codebase moi: chuyen tat ca diem fallback ve `data.txt`, loai bo bien `raw_repo_path` khong con phu hop.
- Cap nhat script ho tro dataset/chunk (`data/print_chunks.py`, `data/synthetic_gen.py`) de tranh mismatch signature va loi runtime.
- Ho tro kiem tra on dinh sau thay doi bang cach chay check loi va ra soat lai cac file tham chieu ten du lieu cu.

## 2. Kien thuc ky thuat rut ra
- Refactor hieu qua la refactor giam lap va tang do ro rang, khong thay doi output nghiep vu.
- Khi doi ten file du lieu, can scan toan repo de dam bao loader, metadata, helper script va thong bao loi deu cap nhat dong bo.
- Trong pipeline danh gia, co fallback ro rang se giup benchmark tiep tuc tao report du gap ngoai le, thay vi vo toan bo luong.
- Tach logic tinh metric vao mot ham rieng giup de test, de review va de sua cong thuc ma khong anh huong nhieu noi.

## 3. Van de gap phai va cach xu ly
- **Van de 1:** Code van con tham chieu file du lieu cu sau khi doi ten.
  - *Xu ly:* Dung tim kiem toan workspace va cap nhat lai duong dan tai Agent, SDG va metadata source.
- **Van de 2:** Sau khi doi signature ham load chunk, call site cu bi sai so tham so.
  - *Xu ly:* Chuan hoa ham `load_and_chunk_real_data` va cap nhat tat ca noi goi de chi nhan mot `source_file`.
- **Van de 3:** Reflection can phan anh dung hien trang codebase sau refactor, khong dung noi dung cu.
  - *Xu ly:* Viet lai reflection theo thay doi moi, neu ro bai hoc ky thuat va buoc nang cap tiep theo.

## 4. Ke hoach cai tien tiep theo
- Bo sung test nho cho cac helper moi (`_compute_summary`, fallback payload, helper thong ke) de giam rui ro regression.
- Tach cau hinh ten file du lieu va cac nguong release gate thanh constant/env de tranh hard-code phan tan.
- Nang cap retrieval tu lexical overlap len hybrid retrieval (BM25 + embedding) de on dinh hon voi edge/adversarial.
- Chuan hoa them logging thong nhat de de doi chieu giua benchmark result va failure analysis.
