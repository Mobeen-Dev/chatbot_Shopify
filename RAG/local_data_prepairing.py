import csv
from langchain_community.document_loaders import CSVLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

def load_and_split_csv_files(
    folder_path: str = "Data",
    file_prefix: str = "products_export_",
    file_range: range = range(1, 4),
    record_chunk_size: int = 1000,
    record_chunk_overlap: int = 100,
    description_chunk_size: int = 500,
    description_chunk_overlap: int = 70,
) -> list:
    """
    Loads and splits multiple CSV files into text chunks using LangChain.
    
    Args:
        folder_path: Directory containing CSV files.
        file_prefix: Common filename prefix.
        file_range: Range of file suffixes (e.g., 1 to 3 for 'products_export_1.csv', etc.)
        record_chunk_size: Chunk size for full record splitting.
        record_chunk_overlap: Overlap between record chunks.
        description_chunk_size: Chunk size for further splitting descriptions.
        description_chunk_overlap: Overlap between description chunks.

    Returns:
        List of document chunks.
    """
    final_chunks = []
    csv.field_size_limit(10**7)  # Increase field size limit

    # Initialize splitters
    record_splitter = RecursiveCharacterTextSplitter(
        chunk_size=record_chunk_size,
        chunk_overlap=record_chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""],
    )

    description_splitter = RecursiveCharacterTextSplitter(
        chunk_size=description_chunk_size,
        chunk_overlap=description_chunk_overlap,
        separators=["\n", ".", " ", ""],
    )

    # Process each file
    for i in file_range:
        csv_path = f"{folder_path}/{file_prefix}{i}.csv"
        loader = CSVLoader(file_path=csv_path, encoding='utf-8', csv_args={'delimiter': ','}, metadata_columns=['Handle'])

        try:
            documents = loader.load()
        except Exception as e:
            print(f"Error loading {csv_path}: {e}")
            continue

        split_records = record_splitter.split_documents(documents)

        for doc in split_records:
            if 'description' in doc.metadata.get('source', '') or 'description' in doc.page_content.lower():
                chunks = description_splitter.split_documents([doc])
            else:
                chunks = [doc]

            # Filter out empty or whitespace-only chunks
            non_empty_chunks = [chunk for chunk in chunks if chunk.page_content.strip()]
            final_chunks.extend(non_empty_chunks)

    return final_chunks
 
# Example usage
if __name__ == "__main__":
    chunks = load_and_split_csv_files()
    print(f"Total chunks created: {len(chunks)}")
    for chunk in chunks[-5]:  # Print first 5 chunks
        print(chunk.page_content)
        print()
        print(chunk.metadata)
