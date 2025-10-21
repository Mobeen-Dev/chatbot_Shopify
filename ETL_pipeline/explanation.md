```mermaid
flowchart TD

    %% Main Pipeline Start
    A[pipeline.py] -->|Mode 2: Resume Job| B[Download processed files from OpenAI server]
    A -->|Mode 1: New Job| C[Fetch all data from Shopify]

    B --> D[Save downloaded files locally]
    
    %% Mode 1 flow
    C --> E[Chunk data into files]
    E --> F[Upload chunked files to OpenAI server]
    F --> G[Save upload record]
    G --> H[Terminate]
    H --> AA[wait 24h for OpenAI batch to finish]
    AA --> AB[ Jump to Mode 2 ]

    %% After batch completion
    D --> I[faiss_index_creation.py]
    I --> J[Use OpenAI batch output files]
    J --> K[Build FAISS index + save metadata]

    %% Final stage
    K --> L[id_to_product_mapping.py]
    L --> M[Use metadata to create product blocks]
    M --> N[Ready-to-feed product data output]
````
