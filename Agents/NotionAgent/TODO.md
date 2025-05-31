# Refactoring of block handling

- [✅]  Najpierw wyodrębnienie metod `clean` do osobnej klasy - `BlockHolder`
    - [✅]  Umieścić nową klasę jako składową klienta
- [✅]  Klasa Pydantic o nazwie `BlockDict` (int id -> Block content)
- [✅]  Od teraz klientów Notion będzie zwracał alternatywę str / dict
- [ ]  Umieszczenie bloków w nowej klasie - przeniesienie funkcjonalności zarządzania blokami z klienta Notion
- [✅]  Użycie klasy  / `BlockDict` w toolach
- []  Użycie klasy `BlockHolder` w toolach
- [✅]  Użycie klasy `BlockDict` w logice agenta
- []  Użycie klasy `BlockHolder` w logice agenta
- [ ]  Refactoring `BlockTree`, jeśli jest potrzebny?
- [ ]  Przechowywać w cache **cały** blok, bez filtracji
- [ ]  Aktualizacja testów → test, powtarzać do skutku
- [ ]  Filtracja na podstawie kategorii (enum) podawanych w parametrze wywołania

# Misc features

# Extra agent tools

## Tool that shows X favourite pages

- Do not give it to Agent yet
- Allow paging?
- Create unit tests

## Limit number of loop iteration for Agent

- Start with Notion Agent
- Add iteration count to context, as last message
- Mention it in system prompt?

# Marimo dashboard

## Add static field that shows cache hit ratio

## Open logs from multiple tasks ran in parallel in separate tabs

- Make sure text doesn't go out of tab header

## Fix task browser label so it can hold long text (currently it doesn't fit and extends beyond boundaries)

## Create new task in Marimo

- Get all tasks from actual database: https://www.notion.so/11d9efeb667680ed98cffaef689b9cf1?v=65ea497489ca4dd4a58998f5b1242988
