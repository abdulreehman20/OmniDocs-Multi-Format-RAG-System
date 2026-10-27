# Phase-by-phase implementation roadmap   

## Introduction

---

## TECH STACK Used:
Backend:
- Python, FastAPI, SQLModel
- Neon (Postgres) as the primary database
- Neon Object Storage (S3-compatible) for raw uploaded files
- Neon Auth with Better Auth integration (JWT verification in FastAPI)
- Inngest (Python SDK) for background jobs and durable workflows, served
  from FastAPI
- Testing -- pytest + pytest-asyncio + httpx (Async API & Database Unit Testing)

Frontend:
- TypeScript, Next.js, shadcn/ui, Vercel AI SDK UI (streaming chat)
- Better Auth UI for Auth UI [Neon Auth with Better Auth integration]
- Playwright (End-to-End E2E Testing for Authentication & Streams)

RAG / AI
- LangChain for ingestion, retrieval pipelines and agent
- OpenRouter free models for generation -- Chat (nvidia/nemotron-3-ultra-550b-a55b:free) / Embeddings (nvidia/nemotron-3.5-embed-1b:free)
- Pinecone as the vector store (also tell me which embedding model to use and where it runs, since OpenRouter free models are not guaranteed to provide embeddings)
- Prompt versioning (prompts stored, versioned, and traceable to each answer)

Observability / Erroes:
- Redis for caching (embeddings, retrieval results, repeated answers)
- Sentry for backend error and performance monitoring
- RAGAS for RAG evaluation (faithfulness, answer relevancy, context precision/recall) and traces

---

## SUPPORTED DATA SOURCES
Markdown, TXT, PDF (including books / long documents), Web Pages, CSV files, and word documents

---

## Phase-by-phase implementation guide

### What I can Completed:

### Phase 0 — Project Initialization and Setup
- First analysis the current project and check wheather its everything which are avaliable in this project are properly integrated or not and its alligen with your furthers things or not

- First check my frontend and backend project setup if something miss so add this

- Then install fastapi, SQLModel, NeonDB, Inngest, LangChain, OpenRouter, Pinecone, Reddis, Sentry, Redis -- If these are not avaliable in my project so install it, if its avaliable so check the install package are allign to our project requirment or not

- Then SETUP neon object storage, redis for cashing, inngest for background jobs, sentry for backend and frontend error tracking, ragas for rag / ai evaluation or observability, setup pinecone with its client, setup SQLModel with neondb so before implementing first chect that it setup in project or not if not so setup it but if it avaliable then check its compatable with our project requirment if yes so leave it or if not so update this according to our need

### Phase 1 —  database, Authentication and uploads

- Then create a database models using sqlModel
   - users -- Application profile and account settings; identity comes from Neon Auth.
   - documents -- Owner, filename, source type, bucket, key, size, MIME type, hash, generation, status and progress.
   - chunks -- Chunk IDs, source locations, content hashes, vector IDs, chunking version and ingestion generation.
   - ingestion_jobs -- Job status, retries, stage, Inngest event/run correlation, error details and timing.
   - ingestion_batches -- Optional table for fan-out processing of large books or Sheets ranges.
   - conversations -- Owner, title, selected document scope and timestamps.
   - messages -- User questions, final answers, active prompt version, model and trace identifiers.
   - message_citations -- Exact links from an answer to documents, chunks and page or row locations.
   - prompt_versions -- Immutable template versions, model configuration, rollout state and content hash.
   - eval_runs -- Dataset version, evaluator model, metrics, timestamps, status and trace references.
   - outbox_events -- Persisted events awaiting publication to Inngest.

- Then SETUP auth in this project so I use Neon Auth with betterauth integration and for auth UI we use betterauth ui. so, find the best way on internet to integrate neonauth with betterauth integration in my fastapi backend and nextjs frontend and then implement it and also implement betterauth ui component in frontend then complete the authentication flow and then test this auth flow and make sure that I want the users or auth related details in my neon database. 

- implementing Secure document upload and management
  - So we are using neondb object storage free plan okay, So first check that how much storage neondb give us and also check maximum object size which we can Upload oka
  - Then Create a distinct private bucket for development and production, So implement a proper object upload, save and added to document through url flow properly as profeshional manner oka and make sure that user can able to download and developer this document oka 
  - Then on the frontend create a testing page name file upload and create a file upload component exactly as same as my file-upload.png image, here add multiple options bt default when it click on drag and drop it can select any type of file in his system, but we also give him more options, markdown, txt files, pdfs. CSV files and words document so when user click on these option through our component so its only select those specific file type data in his system oka

 - Then after implement these things check that my user auth, databases models and upload file feature are properly in working oka

 - Note -- Add all security check which is important to my sight when user add or upload data to my database oka 

### Phase 2 — ingestion pipeline

Create a ingestion pipline inside my ai/ingestion folder.
- So when user upload the data files which is our application supported types, So our first task is to load data using langchain loaders, so create a loaders.py file in ingestion folder and then here add all the loaders and according to our data type select the loader and load it using loaders
- Then after load data make a chunks usings Text Splitters (prefer 'RecursiveCharacterTextSplitter') to break large peace of data into smaller or meaningful segment, Implement industry-standard default settings (set chunk_size=1000 tokens/characters and chunk_overlap=200 to prevent context fragmentation) while exposing these values as adjustable parameters.
- Programmatically loop through the resulting text chunks to inject custom fields into the .metadata dictionary without erasing original data. Specifically append a unique chunk_id ("{filename}_chunk_{index}") and a runtime processed_at ISO timestamp.

- Integrate the embedding model. Then Convert the text into vector embeddings and save this into my pinecone vector store oka and make sure that when you are add embeddings into store use pinecone Namespaces because if we have multiple user so its help us to segerate single user data embeddings and then perform search on specifically matching Namespaces

- Now I want that when user upload the data of any type and then all the ingestion related task performed on it so it perform on background using inngest so add function here, When user upload the document it can featch or verify the file or object url and verify the size and hash and other important things, Then load or parse these documents then create chunks of these loaded documents then create a vector embeddings and store these into vector store, All these process are running as a background job and on frontend we just show the loading bar which automativcally completing when each step completed in background and when its completed we tell user to your document is ready not you can start Q/A on behalf of your docs

- Also add a functionalty to face retry, reconciliation, cancellation checks and failed-job so fulfill the user request.

- after that test this whole flow on backend and frontend to and make sure that its working perfectly before going further


### Phase 3 — Retrieval, chat, and citations
Now implement the retrieval and generation process
- So when user give a question in the chat so first, Embed the question with the same embedding model used for ingestion.Then Query to Pinecone with the authorized namespace and retreive the answer of the question using Standard Semantic Search / Dense Vector Retrieval. Then Remove near-duplicate chunks, particularly overlapping chunks from the same page or section.
- Then Apply maximal marginal relevance (MMR) to balance similarity and diversity. Then Take the best 3–5 chunks that fit the prompt's context, Send the question and source-labelled context to the langchain chain using LLM and then llm generate the response and Stream responses to the backend fastapi and also on Next.js through the AI SDK UI protocol.
- Then Store messages, active prompt version and citation records. Then render citations with source filename, page/section or row reference.
- Add the "I don't know" behavior when the supplied context does not support an answer.
- Then add inngest here which can run this whole retrieval and generation process as an background job and we can render on ui that agent is working and when it completed we can show the response with streamed so make sure that this retrieval and generation process are running in background using inngest 
- After that test this phase 3 flow on both sight from backend and also on frontend and make sure that its working perfectly before going further

### Phase 4 — Observability and Evals
Add Redis for cashing, Sentry for error reporting and RAGAS for Observability and Evals
- So in phase 4 first chect that sentry is properly integrated and working properly in our frontend and backend and tract all errors and logs
- Then add and setup redis in this project for cashing, So use this for implemnt cashing in this rag system which is recomanded [AI Please mention all important cashing stratagies which can be implemented]
- Then add RAGAS in this project for Observability and Evals, Add everything which is recomanded for RAG System Observability and Evals in this project oka [AI Please mention all important Observability and Evals thigns which can implemented]
- After that test this phase 4 flow on both sight from backend and also on frontend and make sure that its working perfectly before going further

### Phase 5 - Frontend, Backend, Payment Method and RAG System Testing
Now Complete a frontend of this RAG System:
- First create a simple Landing Page for this RAG System where mention the all data types and our system related details oka 
- Then add a sidebar in the dashboard layout where you can render the chats, documents and settings navigation links
- Then create a documents page, In this page on top add a search bar on left and the right sight add a upload documenta components, Then after that Add a shadcn data table where mention these things FileSymbol according to datatype, FileName, Size, Type, status of uploading and date so add these columns in the datatable and then add a delete icon at the last in the row when user click on it the file are deleted on the storage, database and also deleted the embeddings of this file in the pinecone database oka so implement it to, Then in the right sight at the bottom of upload files components render each file card and with file icon, name, size and also loading bar oka so user can see the loading in this page oka so I added the documents.png so I want ui the exact same way oka 
- Now in the chat page I want that in the chat navigation link we can render all our previous chat and when user click on it the chat can be opened with the messages and op top of the sidebar add  buttons new documents and new chat and when user click on new documents he can redirect it to documents page and when it click on new chat page so new chat can be created where user can select the documents which he want to ask questions then he can add quetion and then perform all the rag process here but when response is streamed you can add response first, then after that add a source links after the response just like chat.png image and then also add the option to copy response, reload response, time it take to generate response, render all these things at the end of the response oka 
- Also design a setting page so here we can render the user personal details, and account related details oka 
- After that test this phase 5 flow on both sight from backend and also on frontend and make sure that its working perfectly

---