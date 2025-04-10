# Agent Graph

## Writer agent

#### FIXME: Results are scrambled, probably block tree is not ordered?

> ### Moja integracja
> #### Zalety
> - Nauczę się tworzyć autonomicznych agentów
> - Potencjał biznesowy - Notion jest powszechnie używane
> - Mogę wyeksportować moje projekty i notatki bezpośrednio do narzędzi, np. Pythagora
> - Notion zawiera i będzie zawierać najbardziej kompletne dane o mnie i moich planach
> - Agent może porządkować i czyścić strony
> - Agent może zarządzać taskami, listą TODO czy np. artykułami i wideo do obrzejrzenia
> - Agent może za mnie przeszukiwać Notion
> - Mogę wyekstrahować wiedzę z Notion do innej formy, np. graph-RAG
> #### Scenariusze użycia
> ##### Wyszukiwanie informacji
> ##### Edycja indeksu
> ##### Edycja informacji
> ##### Działania autonomiczne?
> #### Dedykowany agent samodzielnie przeglądający Notion
> #### Integracja z YouTube
> - Wygenerować token API: Autoryzacja
> - Obsługa błędów
> - Brak uprawnień
> - Strona nie istnieje
> - Brak sieci
> - Obsługa size limit - W zależności od typu obiektu
> - Obsługa języka polskiego
> - Przygotować zakres funkcjonalności MVP
> - Wiele instancji agentów może obsługiwać różne zadania.
> - Możliwość samodzielnego zarządzania układem stron, odnośników
> - Jakie problemy ma rozwiązywać agent?
> - Agregowanie wiedzy z wielu stron
> - Możliwa integracja Notion z innymi narzędziami, np. Zapierem
> - Rozbicie agenta na dwie części: Prostego przeglądającego strony i bardziej zaawansowanego - nadzorcy.
> - Dodatkowy agent działający w tle, który będzie generował mapę strony, podsumowania, raporty, sugestie
> - Jak przygotować się na wypadek dodania webhooków w przyszłości?
> - Autoryzacja dostępu publicznego
> - Ostatecznie chcę, aby wszystkie powiadomienia trafiały do mojego klienta.

# Bugs

#### Error messages
> KNOWLEDGE:langfuse:Failed to process event in IngestionConsumer, skipping
> Traceback (most recent call last):
> (...)
> TypeError: unhashable type: 'dict'

