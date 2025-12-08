# Async Agent Calls with Databricks Lakebase

A FastAPI-based asynchronous agent implementation that integrates Databricks AI agents with PostgreSQL for scalable, non-blocking chat interactions.

## 🎯 Overview

This project demonstrates how to implement **asynchronous agent calls** using FastAPI's BackgroundTasks combined with Databricks Lakebase (PostgreSQL). The key innovation is the ability to handle long-running AI agent queries without blocking the API, enabling better scalability and user experience.
The frontend used is from https://github.com/databricks-solutions/databricks-blogposts/tree/main/agent_chat


## 🏗️ How It Works

### Request Flow

```
1. Client sends question → POST /api/start-conversation
2. Server returns question_id immediately (optional, for demo purposes only)
3. Insert question_id, question and status into a Lakebase table
3. Agent call runs in background via BackgroundTasks
4. Status is inserted as "Processing" in Lakebase table
5. Client polls GET /api/get-status/{question_id}
6. When complete, status updates to "Done"
7. Client retrieves answer via GET /api/get-answer/{question_id}
```

This way, instead of calling the serving endpoint through the API call, you can call the App APIs `POST /api/start-conversation`, `GET /api/get-status/{question_id}` and `GET /api/get-answer/{question_id}`.

## 📋 Notes

- This example is a simple implementation and can be improved considering best practices (`.env` file for parameters and DABs, for example)
- The frontend is completely optional (for demo purposes only). The real interface could be a Microsoft Teams Bot or something similar
- The main logic is in the backend. However, be aware of the logic in /client/src/PremiumChatBot.js for orchestrating the API calls. Something similar will be needed on the interface you choose to use
- Make sure you have a Lakebase resource and table created before using the App
- Grant permission for the App to have access to the Lakebase resource
- Change the table name being queried if the name is different

