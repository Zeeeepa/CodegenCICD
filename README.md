
1. OPEN UI dashboard 
2. HEADERS PROJECT DROPDOWN LIST -> Select project (Appears in dashboard as project card - at this moment the project is set with webhook URL from cloudflare domain url from .env (When project gets PR - it sends webhook notification to the program)
project card has button "Run" -> when pressing allows adding "Target text / goal" and confirm button sends request with project as context prompt text <Project='selectedprojectname'> + text from  "Target text / goal" -> project card shows progression from codege api endpoint logging. when response is retrieved it shows response - 1 out of 3 types. (regular / plan / PR) - Regular has button "continue" to add text and send as resume endpoint.  plan has button [confirm / modify] - if confirm, sends (Confirm prompt - could be set by default <"Proceed">, if modify also opets text input field and confirm button. If PR is created it should show notification of project's card github square with number of PR - . it should be possible to press on it - prompts validation flow:

VALIDATION FLOW. CREATES SNAPSHOT of instance with graph_sitter + web-eval-agent pre deployed with .env variables required for them. 
step 2- git clones PR codebase. 
step 3- run deployment commands set in project's card's deployment settings tab.
step 4-validate that deployment was successfull using retrieved context + gemini api - if failed -> sends error logs + context to codegen api agent with error context  as continuation on the project's card (As if pressing "continue" on project's card- but automatically  + prompt asking to update that same PR with codefilechanges to resolve) if error loops further until suceeds or if alot of fails cancels that codegen api run session but saves all error ocntexts and sends new identical as initial user's request + adds all error conexts . when successful -> runs web-eval-agent - to test all flows, all components - if errors - again sends as continue button message to that same agent run instance with error context asking to update PR. When PR on the project selected on the card is updated it should trigger re-deployment commands to be runned -> Then again web-eval-agent runs until validates all working functionalities components flows. After all is verified as working [propose notification with complete task allowing user to select [merge to main] or [open github]. project's card should have checkbox [Auto-merge validated PR]. Create NEW PROPERLY UPGRADED README.md with proper flow of functions and usage of program - showing in both elements and functions used and projects which are responsible for these functions.

Please analyze PR you have created - update it with functionality - each project card should have "Agent Run" button. This button opens text dialog which allows user to add text "Target" and then to press confirm. initially it should send this text via codegen api (current agent run implementation) with pre-prompt explicitly and in high detail (this prompt should be setupable via settings dialog's new tab - Planning Statement (only text that is sent to codegen together with user's added text from "Agent Run" text dialog.. each project's pinned to dashboard card should have 1-checkboxx checkbox -Auto Confirm Proposed Plan [ X ]. 2- settings gear icon with idalog. the dialog of project card should have tab for repository rules when pressing opens tab with "Specify any additional rules you want the agent to follow for this repository." and has text input. if text is added should identify that by changing colours in the card itself.

3rd project card feature Setup Commands Specify the commands to run when setting up the sandbox environment. example input : """ cd backend python api.py cd .. cd frontend npm install npm run dev """" and with buttons "Run", "Save", "Branch (dropdown branch names to select branch on which to run setup commands) when running shows if failed, or errors with logs or sucess if all works. further project card feature - Secrets button opens dialog which allows adding "+add secret" when pressing gives 2 text input fields: [ENV_VAR_NAME] + [VALUE] or it has "paste in text". simply opens all env variables as simple text file. Example input CODEGEN_ORG_ID=323 CODEGEN_TOKEN=sk-ce027fa7-3c8d-4beb-8c86-ed8ae982ac99

All this information should stay persistant between openings, runs, restarts

.env.example
#Codegen agent api [Codegen]
CODEGEN_ORG_ID=
CODEGEN_API_TOKEN=

#Github usage [grainchain, codegenApp]
GITHUB_TOKEN=

# use  [web-eval-agent]
GEMINI_API_KEY=


# online accessability [cloudflare]
CLOUDFLARE_API_KEY=
CLOUDFLARE_ACCOUNT_ID=
CLOUDFLARE_WORKER_NAME=webhook-gateway
CLOUDFLARE_WORKER_URL=https://webhook-gateway.pixeliumperfecto.workers.dev

#grainchain [local sandboxing]
