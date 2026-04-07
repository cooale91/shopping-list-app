# Meal Planner Fire 7 + Alexa Shared List

This version adds a shared shopping-list tab that talks to the same backend as the Alexa custom skill.

## New environment variables for Streamlit Cloud
Set these in your app settings / secrets or environment:
- `MEAL_PLANNER_API_BASE_URL`
- `MEAL_PLANNER_API_KEY`
- `MEAL_PLANNER_USER_ID` (optional; default is `demo-user`)

## What changes
- new **Alexa list** tab
- add items manually to the shared backend list
- remove or clear shared items
- send recipe shopping items to the shared Alexa list
- add individual items from the shopping tab to the shared Alexa list

## Important
For real multi-user use, use account linking and a proper user ID mapping.
