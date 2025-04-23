# DOCE - Division of Contract Efficiency

An AI-powered application using Microsoft Semantic Kernel to ingest invoices, extract data using Google Vision, retrieve corresponding contracts from local storage, validate invoice details against contract terms using AI agents, and manage the workflow for review and approval.

## Project Overview

DOCE (Division of Contract Efficiency) is an AI Invoice Validation System designed to streamline the invoice processing and validation workflow. The system uses Microsoft Semantic Kernel to orchestrate a multi-agent system that processes invoices, extracts data, retrieves relevant contracts, validates invoice details against contract terms, and manages the approval workflow.

## Core Features

- **Invoice OCR Processing**: Extract text and data from invoice PDFs and images using Google Vision API
- **Contract Retrieval**: Automatically match invoices to the relevant contracts
- **AI Validation**: Compare invoice details against contract terms to identify discrepancies
- **Workflow Management**: Route invoices for review or approval based on configurable rules
- **User Dashboard**: Monitor invoice status, review flagged invoices, and approve/reject invoices

## Technology Stack

- **Backend**: Python with FastAPI
- **Frontend**: React with Tailwind CSS
- **AI Framework**: Microsoft Semantic Kernel
- **OCR**: Google Cloud Vision API
- **LLM**: Azure OpenAI (GPT-4o)
- **Database**: PostgreSQL

## Project Structure

```
doce/
├── api/                  # FastAPI endpoints
├── agents/               # Semantic Kernel agents
├── plugins/              # Semantic Kernel plugins
├── models/               # Pydantic schemas
├── database/             # Database models and connection
├── config/               # Configuration settings
├── frontend/             # React frontend application
└── tests/                # Unit and integration tests
```

## Getting Started

### Prerequisites

- Python 3.8+
- Node.js 14+
- PostgreSQL
- Google Cloud Vision API credentials
- Azure OpenAI API credentials

### Installation

1. Clone the repository
2. Install backend dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Install frontend dependencies:
   ```
   cd frontend
   npm install
   ```
4. Configure environment variables in `.env` file
5. Run database migrations
6. Start the backend server:
   ```
   uvicorn doce.main:app --reload
   ```
7. Start the frontend development server:
   ```
   cd frontend
   npm start
   ```

## API Documentation

Once the server is running, you can access the API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## License

This project is licensed under the MIT License - see the LICENSE file for details.