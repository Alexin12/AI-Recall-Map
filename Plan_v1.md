## Goal
I’m building Recall Map — an AI learning tool that turns course notes, transcripts, and articles into active recall questions and concept maps.
The goal is to help learners stop losing knowledge after each lesson. Instead of just summarizing notes, it extracts key concepts, shows


## Functions

Main function:
- 1. Manual review:This tool/App can help user easily track what they have learned in the past, 7 days, 1 month, 1 year,etc. key concept,and anaology, and relationship between concepts will show once user click the time they choose.
    - for example : When user click yesterday tab, they can find concepts they have learned , analogy or a graph/diagram to each specific concept, a mind map of these concept for yesterday
    - When user click last week tab, they can find concepts they have learned , analogy or a graph/diagram to each specific concept, a mind map of these concept for last week 

- 2. Exam understandings: Way to help learner find things they need to review 
  - Test:
    - Flash card : flash card  to ask learner if they know the concept
    - Understanding input :Ask learner to input their understanding and system will judge if they understand
  - System judge
    - An LLM will judge user input based on related concept, LLM might use RAG to retrive information that input by user
    - LLM will indicate parts that not qualify to pass the test from user's answer for Understanding input questions
    - LLM will return suggested content to review , suggestion might look like "Your understanding for xxx may need to strength , please review sections of i of dd-mm--yy content".
  
- 3. Automate time review alert 

  
Data Digestion:
- This App can input informations includes:(May expand in future V2)
  - PDF
  - Markdown file
  - Word doc
  - Google Doc
  - Excel
  - png



- Input check:
    - Not sure yet: Check if user input content have some inaccure , which means they might pollute the database of users if their input wrong
    - Check if input format is allowed


## Why need it 
- Hard to recall concept: People easy to forget key concepts they have learned, and they took too much time to review things they have already leaned
  
- Information Isolation : The knowledge they have learned is not connect to each other , information isolated, hard to trace
  
- Unorganized infomation :Learning materials sit everywhere , notes, pdf, ppt, transcripts, podcast 
  
- Test standard:There is no a standard to test if user really understand what they have learned or just take note and exit


## Basic UI
- A webpage (May expand to Iphone App)


# Decisions not sure (Know unknow)
- What kind of format should show for each tab?