**Project:** Division of Contract Efficiency (DOCE) - AI Invoice Validation System

**Goal:** Develop an AI-powered application using Microsoft Semantic Kernel to ingest invoices, extract data using Google Vision, retrieve corresponding contracts from local storage, validate invoice details against contract terms using AI agents, and manage the workflow for review and approval.

**Core Technology:** Microsoft Semantic Kernel (using Python)

---

## 1. High-Level Architecture Diagram

```mermaid
graph TD
    subgraph User Interface (React/Vue/Angular)
        UI[Web Dashboard]
        Upload[Invoice Upload Component]
        Review[Review & Approval UI]
    end

    subgraph Backend API Layer (Python/Node.js + FastAPI/Flask)
        API[REST/GraphQL API Gateway]
    end

    subgraph Semantic Kernel Agentic Core
        Orchestrator[Orchestrator Agent]
        InvoiceProcessor[Invoice Processing Agent]
        ContractRetriever[Contract Retrieval Agent]
        ValidationAgent[Validation Agent]
        WorkflowAgent[Workflow Agent]
    end

    subgraph Semantic Kernel Plugins (Tools)
        GoogleVisionPlugin[Google Vision OCR Plugin]
        FileSystemPlugin[Contract Storage Plugin (Local)]
        DatabasePlugin[Application DB Plugin]
        NLPPlugin[Core NLP/Structuring Plugin (uses LLM)]
        WorkflowRulesPlugin[Workflow Rules Plugin]
        %% Potentially: EmailPlugin[Email Ingestion Plugin]
        %% Potentially: ERPPlugin[ERP/Accounting Plugin]
    end

    subgraph Data Stores
        DB[(Application Database - Postgres/MongoDB)]
        Contracts[/Contract Document Store (Local tmp/)\]
    end

    subgraph External Services
        GoogleVision[Google Cloud Vision API]
        LLM[LLM Service (e.g., Azure OpenAI, OpenAI)]
        %% EmailService[Email Service]
        %% ERP[ERP/Accounting System API]
    end

    %% Connections
    User --- UI
    UI --- API
    Upload --- API
    Review --- API

    API --- Orchestrator

    Orchestrator --> InvoiceProcessor
    Orchestrator --> ContractRetriever
    Orchestrator --> ValidationAgent
    Orchestrator --> WorkflowAgent
    Orchestrator --> NLPPlugin
    Orchestrator --> DatabasePlugin

    InvoiceProcessor --> GoogleVisionPlugin
    InvoiceProcessor --> NLPPlugin

    ContractRetriever --> FileSystemPlugin
    ContractRetriever --> DatabasePlugin %% For metadata lookup if needed

    ValidationAgent --> NLPPlugin %% To understand/compare terms
    ValidationAgent --> DatabasePlugin %% To fetch validation rules/history

    WorkflowAgent --> WorkflowRulesPlugin
    WorkflowAgent --> DatabasePlugin %% To update status, log actions
    WorkflowAgent --> API %% To notify UI or trigger external actions (future)
    %% WorkflowAgent --> ERPPlugin

    GoogleVisionPlugin --> GoogleVision
    NLPPlugin --> LLM
    FileSystemPlugin --> Contracts
    DatabasePlugin --> DB
    WorkflowRulesPlugin --> DB %% Load rules from DB

    %% Optional Ingestion Path
    %% EmailService --> EmailPlugin --> API
```

*Diagram Notes:*
*   Arrows indicate primary data flow or control flow.
*   Semantic Kernel Agents orchestrate tasks and use Plugins (Tools).
*   Plugins interact with external services or internal resources.

---

## 2. Component Breakdown

**2.1. Frontend (React/Vue/Angular)**

*   **Responsibilities:**
    *   Provide a user-friendly interface for Accounts Payable (AP) teams.
    *   Allow users to upload invoice files (PDF, JPEG, TIFF).
    *   Display a dashboard summarizing invoice statuses (Pending, Validated, Flagged, Approved).
    *   Present extracted invoice data alongside relevant contract snippets.
    *   Enable users to review flagged discrepancies, add comments, and approve or reject invoices.
    *   Display audit trails for individual invoices.
*   **Technology:** Use React framework. Use tailwind as the UI component library

**2.2. Backend API Layer (Python/Node.js + API Framework)**

*   **Responsibilities:**
    *   Expose RESTful endpoints for the frontend.
    *   Handle user authentication and authorization.
    *   Receive invoice uploads and trigger the processing workflow via the Orchestrator Agent.
    *   Serve data required by the UI (invoice status, details, contract snippets, audit logs).
    *   Receive approval/rejection actions from the UI and update status via the Workflow Agent or directly in the DB.
*   **Technology:** Use Python (with FastAPI/Flask).

**2.3. Semantic Kernel Agentic Core**

*   **Responsibilities:** Manage the end-to-end invoice validation process using a multi-agent system.
*   **Technology:** Microsoft Semantic Kernel SDK (Python).
*   **Agents:**
    *   **Orchestrator Agent:**
        *   The main entry point for invoice processing requests from the API.
        *   Manages the overall flow: calls Invoice Processing, Contract Retrieval, Validation, and Workflow agents in sequence.
        *   Handles high-level state management and error propagation.
        *   Uses core NLP/Structuring plugin to understand context and results from other agents.
    *   **Invoice Processing Agent:**
        *   Receives the raw invoice file path/data.
        *   Uses the `Google Vision OCR Plugin` to perform OCR.
        *   Uses the `Core NLP/Structuring Plugin` (powered by an LLM via SK) to extract and structure key fields (Invoice #, Date, Vendor, Line Items, Totals) from the OCR text.
        *   Returns structured invoice data.
    *   **Contract Retrieval Agent:**
        *   Receives vendor information (and potentially other identifiers) from the extracted invoice data.
        *   Uses the `File System Plugin` to search the local contract directory for a matching contract file (based on naming convention, e.g., `VendorName_Contract.pdf`). *Initial simple matching, can be enhanced later.*
        *   May use the `Database Plugin` if contract metadata is stored separately.
        *   Returns the path to the relevant contract file or indicates if none was found.
    *   **Validation Agent:**
        *   Receives structured invoice data and the path to the relevant contract file.
        *   Uses the `File System Plugin` to load the contract content.
        *   Uses the `Core NLP/Structuring Plugin` (LLM) to:
            *   Extract relevant terms, pricing, dates, and item descriptions from the contract.
            *   Compare the extracted invoice data against the extracted contract data.
            *   Identify discrepancies (price mismatches, item mismatches, date issues, policy violations).
        *   Returns a validation result (Validated, Flagged) and a list of discrepancies.
    *   **Workflow Agent:**
        *   Receives the validation result and discrepancies.
        *   Uses the `Workflow Rules Plugin` (which might fetch rules from the `Database Plugin`) to determine the next step (e.g., Auto-Approve if Validated and below threshold, Route to Review if Flagged or above threshold).
        *   Uses the `Database Plugin` to update the invoice status and log the decision/discrepancies in the audit trail.
        *   (Future) Could use an `ERP Plugin` or `Email Plugin` to trigger external actions.

**2.4. Semantic Kernel Plugins (Tools)**

*   **Responsibilities:** Encapsulate specific functionalities callable by agents.
*   **Technology:** Implemented as classes/functions within the chosen backend language (Python/C#) decorated for Semantic Kernel.
    *   **Google Vision OCR Plugin:** Wrapper around the Google Cloud Vision API client library to perform OCR on image/PDF files.
    *   **Contract Storage Plugin (Local):** Interacts with the local file system (`/tmp/` or a configured path) to list, read, and potentially write contract files. Needs methods like `find_contract_by_vendor(vendor_name)` and `read_contract(file_path)`.
    *   **Application DB Plugin:** Uses an ORM (like SQLAlchemy, Prisma, Entity Framework Core) or direct DB client library to interact with the application database (CRUD operations for Invoices, Contracts Metadata, Audit Logs, Users, Workflow Rules).
    *   **Core NLP/Structuring Plugin:** Leverages the configured LLM via Semantic Kernel's core capabilities (`kernel.InvokePromptAsync`, `kernel.InvokeAsync`) to perform tasks like:
        *   Structuring OCR text into JSON/objects.
        *   Summarizing contract clauses.
        *   Comparing invoice line items to contract terms based on natural language descriptions.
        *   Extracting specific entities (dates, amounts, vendor names).
    *   **Workflow Rules Plugin:** Encapsulates the logic for deciding the next step based on validation results and potentially configurable rules (e.g., fetched from the DB).

**2.5. Data Stores**

*   **Application Database (PostgreSQL/MongoDB):**
    *   **Schema:**
        *   `Invoices`: InvoiceID, FileName, UploadTimestamp, Status (Received, Processing, OCRd, Validated, Flagged, Approved, Rejected), VendorName, InvoiceNumber, InvoiceDate, TotalAmount, ExtractedData (JSON), FlaggedDiscrepancies (JSON/Text), ApprovedByUserID, ApprovalTimestamp.
        *   `Contracts`: ContractID, VendorName, FilePath, StartDate, EndDate, KeyTermsSummary (Text/JSON, optional). *Initially minimal, mainly linking Vendor to FilePath.*
        *   `AuditLogs`: LogID, Timestamp, InvoiceID, Action (e.g., "Uploaded", "OCR Started", "Validation Failed", "Approved"), UserID (if applicable), Details.
        *   `Users`: UserID, Name, Email, Role (e.g., AP Clerk, Manager).
        *   `WorkflowRules`: RuleID, Condition (e.g., "Amount > 1000", "IsFlagged"), Action (e.g., "RequireManagerApproval").
    *   **Technology:** PostgreSQL (Relational) or MongoDB (NoSQL) as suggested. Choose based on data structure needs and team familiarity. PostgreSQL is often preferred for structured data and ACID compliance.
*   **Contract Document Store (Local tmp/):**
    *   **Responsibilities:** Store the actual contract PDF/document files.
    *   **Technology:** Initially a designated local directory as specified. **Important:** This should be abstracted via the `FileSystemPlugin` so it can be easily swapped for cloud storage (like Azure Blob Storage or AWS S3) later for better scalability and reliability.

**2.6. External Services**

*   **Google Cloud Vision API:** Used for OCR via the `GoogleVisionPlugin`. Requires API key/credentials management.
*   **LLM Service:** The core AI engine used by Semantic Kernel agents and the `Core NLP/Structuring Plugin`. Use OpenAI 4o model from Azure foundry through Azure API key. Store keys in .env file.


---

## 3. Data Flow Example (Invoice Upload)

1.  **User Upload:** User uploads `invoice.pdf` via the Frontend UI.
2.  **API Call:** Frontend sends the file to the Backend API `/invoices/upload` endpoint.
3.  **File Storage:** API saves the file temporarily (e.g., `/tmp/uploads/invoice.pdf`) and creates an initial record in the `Invoices` table (Status: Received).
4.  **Trigger Orchestrator:** API calls the `Orchestrator Agent` with the InvoiceID and file path.
5.  **Invoice Processing:** Orchestrator calls `Invoice Processing Agent`.
    *   Agent calls `Google Vision OCR Plugin` with the file path.
    *   Plugin calls Google Vision API, gets OCR text.
    *   Agent calls `Core NLP/Structuring Plugin` with OCR text.
    *   Plugin uses LLM via SK to extract fields (Vendor: "Acme Corp", Invoice#: "INV-123", ...).
    *   Agent updates `Invoices` table (Status: OCRd, ExtractedData populated) via `Database Plugin`.
    *   Agent returns structured data to Orchestrator.
6.  **Contract Retrieval:** Orchestrator calls `Contract Retrieval Agent` with Vendor ("Acme Corp").
    *   Agent calls `File System Plugin`'s `find_contract_by_vendor("Acme Corp")`.
    *   Plugin searches `/tmp/contracts/`, finds `Acme Corp_Contract.pdf`.
    *   Agent returns the contract path to Orchestrator.
7.  **Validation:** Orchestrator calls `Validation Agent` with structured invoice data and contract path.
    *   Agent uses `File System Plugin` to read `Acme Corp_Contract.pdf`.
    *   Agent uses `Core NLP/Structuring Plugin` (LLM) to analyze contract and compare against invoice data. Let's say it finds a price mismatch.
    *   Agent returns result (Status: Flagged, Discrepancy: "Line item 'Widget' price mismatch: $10 vs $9 in contract").
8.  **Workflow Decision:** Orchestrator calls `Workflow Agent` with the validation result.
    *   Agent calls `Workflow Rules Plugin`. The rules indicate flagged invoices need review.
    *   Agent calls `Database Plugin` to update `Invoices` table (Status: Flagged, FlaggedDiscrepancies updated) and adds to `AuditLogs`.
9.  **API Response/UI Update:** The Orchestrator signals completion (potentially asynchronously). The API can now serve the "Flagged" status and details to the Frontend for the user to review.

---

## 4. Implementation Plan - High Level Steps

1.  **Setup & Foundation:**
    *   Set up project structure (Frontend, Backend).
    *   Choose backend language/framework (Python/C#).
    *   Install Semantic Kernel SDK.
    *   Configure LLM service (Azure OpenAI recommended for integration).
    *   Set up database (Postgres/MongoDB) and define initial schemas.
    *   Implement basic API structure and authentication.
2.  **Core Plugins:**
    *   Implement `Google Vision OCR Plugin`.
    *   Implement basic `File System Plugin` for local contract storage.
    *   Implement basic `Database Plugin` for core CRUD on Invoices/AuditLogs.
3.  **Invoice Processing Agent:**
    *   Develop the agent logic.
    *   Develop initial prompts for the `Core NLP/Structuring Plugin` to extract key fields from OCR text.
    *   Test with sample invoices.
4.  **Contract Retrieval & Validation:**
    *   Develop `Contract Retrieval Agent` logic.
    *   Develop `Validation Agent` logic.
    *   Develop prompts/functions for the `Core NLP/Structuring Plugin` to analyze contracts and compare data.
    *   Test matching and validation logic with sample invoice/contract pairs.
5.  **Workflow & Orchestration:**
    *   Develop `Workflow Agent` and basic `Workflow Rules Plugin`.
    *   Implement the `Orchestrator Agent` to tie all agents together.
    *   Refine database schemas (`Status`, `Discrepancies` fields).
6.  **Frontend Development:**
    *   Build UI components for upload, dashboard, and review screens.
    *   Integrate with Backend API endpoints.
7.  **Testing & Refinement:**
    *   Unit tests for plugins and agent logic.
    *   Integration tests for the end-to-end flow.
    *   User Acceptance Testing (UAT) with AP team.
    *   Refine prompts and agent logic based on test results.
8.  **Deployment:**
    *   Containerize the application (Docker).
    *   Set up CI/CD pipeline.
    *   Deploy to a suitable environment (Cloud VM, Kubernetes, App Service).
    *   Configure monitoring and logging.

---

## 5. Key Considerations & Future Enhancements

*   **LLM Choice & Cost:** Use gpt-4o as LLM choice. 
*   **Prompt Engineering:** Significant effort will be needed to create effective prompts for data extraction, contract analysis, and comparison. This will be iterative.
*   **Error Handling:** Robust error handling is crucial at each step (OCR failures, file not found, API errors, agent failures).
*   **Scalability:** The local file system for contracts is a bottleneck. Plan to migrate to cloud storage (Azure Blob, S3). Consider a task queue (Celery, RQ, Azure Functions) for processing invoices asynchronously if volume increases.
*   **Contract Matching:** Simple vendor name matching might be insufficient. Future enhancements could involve using invoice metadata or content analysis to find the *exact* relevant contract or SOW.
*   **Security:** Securely manage API keys (Google Vision, LLM, ERP). Implement proper authentication/authorization for the API and UI.
*   **Monitoring:** Implement logging across all components. Monitor agent performance, LLM response times, and costs.
*   **Feedback Loop:** Allow users to correct extracted data or validation results to potentially fine-tune models/prompts over time (requires significant extra development).
*   **Complex Contracts:** Handling amendments, complex pricing tables, or multi-level contract structures will require more sophisticated NLP/agent logic.
*   **Pre-computation:** Consider pre-processing contracts upon upload to extract key terms and store them in the database for faster validation.