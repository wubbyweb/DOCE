```mermaid
graph TD
    subgraph "User Interface"
        UI[Frontend (React/Vue/Angular)]
    end

    subgraph "API Layer"
        APIGW[API Gateway (e.g., Google Cloud API Gateway)]
    end

    subgraph "Backend Microservices (Python/Node.js/Java on Cloud Run/GKE)"
        Ingestion[Invoice Ingestion Service]
        Extraction[Data Extraction Service]
        Contract[Contract Retrieval Service]
        Validation[Validation Service]
        Workflow[Workflow Service]
    end

    subgraph "AI/ML Layer (Google Cloud AI)"
        OCR[Google Document AI (Invoice Parser)]
        NLP[Google Natural Language API (if needed for specific tasks)]
        Matcher[Custom Models on Vertex AI (Training & Prediction)]
    end

    subgraph "Data Stores (Google Cloud)"
        DB[(Database - Cloud SQL/Firestore/Spanner)]
        ContractStore[(Contract Storage - Google Cloud Storage)]
        AuditLog[(Audit Logs - Cloud Logging/BigQuery)]
    end

    subgraph "External Systems & Integrations"
        Email[Email Server (e.g., SendGrid integration, Gmail API)]
        Uploads[File Uploads (to Cloud Storage)]
        ERP[ERP/Accounting System (via APIs)]
        Payment[Payment System (via APIs)]
    end

    subgraph "Infrastructure & Operations (Google Cloud)"
        Cloud[Google Cloud Platform (GCP)]
        Container[Cloud Run / Google Kubernetes Engine (GKE)]
        Monitor[Cloud Monitoring & Cloud Logging]
        Security[Identity Platform / IAM / Secret Manager]
    end

    %% Connections (remain logically the same)
    User[User] --> UI
    UI --> APIGW

    APIGW --> Ingestion
    APIGW --> Extraction
    APIGW --> Contract
    APIGW --> Validation
    APIGW --> Workflow

    Email --> Ingestion
    Uploads --> Ingestion
    Ingestion --> DB
    Ingestion --> ContractStore # Store raw invoice

    Extraction -- Uses --> OCR
    Extraction -- Uses --> NLP # Optional, for specific text analysis
    Extraction --> DB # Store extracted data

    Contract -- Accesses --> ContractStore # Retrieve contracts
    Contract -- Integrates --> ERP # Optional contract sync
    Contract --> DB # Store contract metadata

    Validation -- Uses --> Matcher # Call Vertex AI models
    Validation -- Reads --> DB # Get extracted data & contract metadata
    Validation -- Reads --> ContractStore # Access contract document if needed by model
    Validation --> DB # Update validation status
    Validation --> Workflow

    Workflow -- Reads --> DB
    Workflow -- Integrates --> ERP
    Workflow -- Integrates --> Payment
    Workflow --> AuditLog
    Workflow --> UI  # Notifications/Status Updates

    %% Infrastructure
    Ingestion -- Runs On --> Container
    Extraction -- Runs On --> Container
    Contract -- Runs On --> Container
    Validation -- Runs On --> Container
    Workflow -- Runs On --> Container
    APIGW -- Managed Service or Runs On --> Container
    Container -- Deployed On --> Cloud
    Monitor -- Monitors --> Backend Microservices & AI Layer
    Security -- Secures --> APIGW & Data Stores
```