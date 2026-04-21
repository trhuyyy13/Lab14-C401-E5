"""
Ingest script: đọc 2 file .txt, chunk theo từng Điều, embed và lưu vào ChromaDB.
Chạy một lần trước khi dùng agent: python data/ingest.py
"""
import re
import os
import json
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHROMA_PATH = "data/chroma_db"
COLLECTION_NAME = "legal_docs"

SOURCE_FILES = {
    "luat_can_bo_cong_chuc": "data/Luật-Cán-bộ-công-chức.txt",
    "nghi_dinh_bhyt": "data/Nghị-định-Về-việc-ban-hành-Điều-lệ.txt",
}


def clean_text(text: str) -> str:
    """Xóa các annotation tag kiểu <HP rel="CC">...</HP> trong văn bản gốc."""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def split_by_article(text: str, source_name: str) -> list:
    """
    Tách văn bản thành các chunk theo từng Điều.
    Mỗi chunk = tiêu đề Điều + nội dung của điều đó.
    Dùng global index để tránh trùng ID khi cùng số Điều xuất hiện nhiều lần
    (ví dụ: Điều 2 của Nghị định chính vs Điều 2 của Điều lệ đính kèm).
    """
    pattern = r"(Điều\s+\d+\s*\.)"
    parts = re.split(pattern, text)

    chunks = []
    seen_ids: dict = {}
    i = 1
    while i < len(parts) - 1:
        if re.match(r"Điều\s+\d+\s*\.", parts[i]):
            header = parts[i].strip()
            content = parts[i + 1].strip() if (i + 1) < len(parts) else ""
            num_match = re.search(r"\d+", header)
            if not num_match:
                i += 2
                continue
            article_num = int(num_match.group())
            base_id = f"{source_name}_dieu_{article_num}"
            # Giải quyết trùng lặp: thêm _2, _3, ... nếu ID đã tồn tại
            if base_id in seen_ids:
                seen_ids[base_id] += 1
                chunk_id = f"{base_id}_{seen_ids[base_id]}"
            else:
                seen_ids[base_id] = 1
                chunk_id = base_id
            full_text = header + " " + content
            chunks.append(
                {
                    "id": chunk_id,
                    "text": clean_text(full_text),
                    "source": source_name,
                    "article_num": article_num,
                }
            )
            i += 2
        else:
            i += 1

    return chunks


def get_collection(force_reingest: bool = False):
    """Trả về ChromaDB collection. Nếu chưa có dữ liệu thì tự động ingest."""
    if not OPENAI_API_KEY:
        raise ValueError("Thiếu OPENAI_API_KEY trong file .env")

    db_client = chromadb.PersistentClient(path=CHROMA_PATH)
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=OPENAI_API_KEY,
        model_name="text-embedding-3-small",
    )
    collection = db_client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=openai_ef,
        metadata={"hnsw:space": "cosine"},
    )

    if collection.count() > 0 and not force_reingest:
        return collection

    # --- Ingest ---
    all_chunks = []
    for source_name, filepath in SOURCE_FILES.items():
        if not os.path.exists(filepath):
            print(f"⚠️  Không tìm thấy file: {filepath}")
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
        chunks = split_by_article(text, source_name)
        all_chunks.extend(chunks)
        print(f"✅ Parsed {len(chunks)} articles từ {filepath}")

    if not all_chunks:
        raise RuntimeError("Không có chunk nào được tạo ra. Kiểm tra lại file .txt.")

    ids = [c["id"] for c in all_chunks]
    documents = [c["text"] for c in all_chunks]
    metadatas = [
        {"source": c["source"], "article_num": c["article_num"]} for c in all_chunks
    ]

    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    print(f"✅ Đã lưu {len(all_chunks)} chunks vào ChromaDB tại '{CHROMA_PATH}'.")

    # Lưu danh sách doc IDs để dùng khi tạo golden set
    doc_id_path = "data/doc_ids.json"
    with open(doc_id_path, "w", encoding="utf-8") as f:
        json.dump(
            [
                {
                    "id": c["id"],
                    "source": c["source"],
                    "article_num": c["article_num"],
                    "preview": c["text"][:120],
                }
                for c in all_chunks
            ],
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"✅ Đã lưu danh sách doc IDs vào '{doc_id_path}'.")

    return collection


if __name__ == "__main__":
    get_collection(force_reingest=True)
    print("🎉 Ingest hoàn tất!")
