import marimo

__generated_with = "0.11.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _(mo):
    mo.md(
        r"""
        **TODO**: Save output of each agent to a file

        **TODO**: Wyłączyć zbędne logi w konsoli

        **TODO**: Zapisywać i wczytywać listę wybranych promptów
        """
    )
    return


@app.cell
def _():
    prompts_pl = ["Znajdź w Notion moje projekty AI i przedstaw krótkie podsumowanie tych projektów.",

    "Jak wygląda moja to-do lista na dziś?",

    "Jak wygląda moja to-do lista na dziś? Znajduje się na tej stronie: https://www.notion.so/TODO-dzi-4fa780c8df7746ff83500cd7d504c3d7?pvs=4",

    'Znajdź zadania w bazie "Sprawy życiowe" ze statusem "Blocked" i przedstaw ich podsumowanie.',

    'W tablicy "Nauka AI" wyszukaj linki do wideo YT i ułoż z nich playlistę. Pomiń zadania, które już zostały wykonane.',

    'W projekcie "Osobisty asystent" znajdź wszystkie podprojekty i posortuj je według priorytetu wykonania.',

    'Odwiedź moją stronę: https://www.notion.so/TODO-dzi-4fa780c8df7746ff83500cd7d504c3d7?pvs=4. Streść zadania do wykonania dziś.'
    ]

    todo_prompts=['Przejdź do "Kalendarza" i wyświetl wszystkie wydarzenia zaplanowane na ten miesiąc.']

    prompts_eng = ["navigate to notion integration page. Get all text from this page.",

    "Hello, search my Notion for AI projects and give me a summary of the projects", "Summarize all info present on Stop OCD project page. List current project status and remaining tasks.",

    "List topics mentioned in my C++ 20 notes. Are there any C++20 features missing in that article?",

    'What time is now?'
    ]

    promts_favourites=['Dodaj tę stronę TODO do ulubionych: https://www.notion.so/TODO-dzi-4fa780c8df7746ff83500cd7d504c3d7',

    'Dodaj tę stronę TODO do ulubionych: https://www.notion.so/TODO-dzi-4fa780c8df7746ff83500cd7d504c3d7. Następnie wyświetl zadania z dzisiejszej listy TODO.',

    'Dodaj też tą - Sprawy Życiowe: https://www.notion.so/fb76be1f96684194952d4ddfac58df48?v=da89c8956e7f4975900b04cba03cc526',

    'Add this page to favourites: https://www.notion.so/Integracja-z-Notion-1029efeb6676804488d6c61da2eb04b9']

    prompts = promts_favourites + prompts_pl + prompts_eng
    return prompts, prompts_eng, prompts_pl, promts_favourites, todo_prompts


@app.cell(hide_code=True)
def _():
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.runnables import RunnableParallel
    import asyncio
    import nest_asyncio
    import time
    import subprocess
    from pathlib import Path

    nest_asyncio.apply()

    from tz_common.logs import log
    from chat import chat
    return (
        ChatPromptTemplate,
        Path,
        RunnableParallel,
        asyncio,
        chat,
        log,
        nest_asyncio,
        subprocess,
        time,
    )


@app.cell
def _():
    responses = []
    return (responses,)


@app.cell(hide_code=True)
def _(mo, prompts):
    prompt_selector = mo.ui.multiselect(
        options=prompts, label="Select promps to run",
        full_width=True
    )

    run_button = mo.ui.run_button(label='Run chats')

    mode_switch = mo.ui.switch(label="Use Server Mode", value=False)

    launch_container_button = mo.ui.button(label="Launch Container")
    stop_container_button = mo.ui.button(label="Stop Container")

    server_status_text = mo.ui.text("Server Status: Checking...", full_width=True)
    container_status_text = mo.ui.text("Container Status: Unknown", full_width=True)

    execution_controls = mo.hstack([run_button, mode_switch], 
                                 widths=[120, 200], gap=1)

    docker_controls = mo.hstack([launch_container_button, stop_container_button],
                               widths=[140, 200], gap=1)

    status_indicators = mo.hstack([server_status_text, container_status_text], widths=[200, 200], gap=1)

    # Main layout
    main_layout = mo.vstack([
        execution_controls,
        prompt_selector,
        mo.md("**Docker Container Management**"),
        docker_controls,
        mo.md("**Status**"),
        status_indicators
    ])

    main_layout
    return (
        container_status_text,
        docker_controls,
        execution_controls,
        launch_container_button,
        main_layout,
        mode_switch,
        prompt_selector,
        run_button,
        server_status_text,
        status_indicators,
        stop_container_button,
    )


@app.cell(hide_code=True)
def _(asyncio, chat, log, mo, responses, run_button, time):
    mo.stop(run_button.value is None, mo.md("**Click button to run chats.**"))

    async def run_chat(option):
        log.flow(f"Starting chat for {option}")
        start_time = time.time()
        result = await asyncio.to_thread(chat, loop=False, user_prompt=option)
        end_time = time.time()
        execution_time = end_time - start_time
        return {
            'prompt': option,
            'result': result,
            'execution_time': execution_time
        }

    async def run_chats_parallel(options):
        responses.clear()
        tasks = [asyncio.create_task(run_chat(option)) for option in options]

        # Use as_completed to handle results as they arrive
        for completed_task in asyncio.as_completed(tasks):
            try:
                result = await completed_task
                responses.append(result)
                log.user(f"Completed task:", {result['prompt']})
                log.debug(f"Took {result['execution_time']} seconds")
            except Exception as e:
                pass

        results = await asyncio.gather(*tasks)
        return results

    #return (ChatPromptTemplate, RunnableParallel, asyncio, run_chat,run_chats_parallel)
    return run_chat, run_chats_parallel


@app.cell(hide_code=True)
def _(
    Path,
    __file__,
    launch_container_button,
    log,
    mo,
    stop_container_button,
    subprocess,
):
    # Handle Docker container management

    def launch_container():
        """Launch Docker container using docker-compose"""
        try:
            # Get the project directory (parent of launcher)
            project_dir = Path(__file__).parent.parent
            log.flow("Launching Docker container", f"Working directory: {project_dir}")

            result = subprocess.run(
                ["docker-compose", "up", "-d"], 
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                log.flow("Container launched successfully")
                return "Container launched successfully"
            else:
                log.error("Failed to launch container", result.stderr)
                return f"Error: {result.stderr}"

        except subprocess.TimeoutExpired:
            return "Error: Container launch timed out"
        except Exception as e:
            log.error("Exception launching container", str(e))
            return f"Error: {str(e)}"

    def stop_container():
        """Stop Docker container using docker-compose"""
        try:
            project_dir = Path(__file__).parent.parent
            log.flow("Stopping Docker container", f"Working directory: {project_dir}")

            result = subprocess.run(
                ["docker-compose", "down"], 
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=60  # 1 minute timeout
            )

            if result.returncode == 0:
                log.flow("Container stopped successfully")
                return "Container stopped successfully"
            else:
                log.error("Failed to stop container", result.stderr)
                return f"Error: {result.stderr}"

        except subprocess.TimeoutExpired:
            return "Error: Container stop timed out"
        except Exception as e:
            log.error("Exception stopping container", str(e))
            return f"Error: {str(e)}"

    # Handle button clicks
    if launch_container_button.value:
        launch_result = launch_container()
        mo.output.append(mo.md(f"**Launch Result**: {launch_result}"))

    if stop_container_button.value:
        stop_result = stop_container()
        mo.output.append(mo.md(f"**Stop Result**: {stop_result}"))
    return launch_container, launch_result, stop_container, stop_result


@app.cell(hide_code=True)
def _(Path, __file__, mo, subprocess):
    # Status checking functions

    def check_server_health():
        """Check if the REST server is responding"""
        try:
            import urllib.request
            response = urllib.request.urlopen('http://localhost:8000/health', timeout=5)
            if response.status == 200:
                return "Server: Online ✓"
            else:
                return f"Server: Error (Status {response.status})"
        except Exception as e:
            return "Server: Offline ✗"

    def check_container_status():
        """Check Docker container status"""
        try:
            project_dir = Path(__file__).parent.parent
            result = subprocess.run(
                ["docker-compose", "ps", "--services", "--filter", "status=running"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                running_services = result.stdout.strip()
                if running_services:
                    return f"Container: Running ✓ ({running_services})"
                else:
                    return "Container: Stopped ○"
            else:
                return "Container: Unknown ?"

        except Exception as e:
            return "Container: Check failed ✗"

    return check_server_health, check_container_status


@app.cell(hide_code=True)
def _(check_container_status, check_server_health, mo):
    # Create status refresh button
    status_refresh_button = mo.ui.button(label="Refresh Status")
    status_refresh_button
    return (status_refresh_button,)


@app.cell(hide_code=True)
def _(check_container_status, check_server_health, mo, status_refresh_button):
    # This cell gets refreshed when status button is clicked
    # Get button value to make this cell reactive to button clicks
    _ = status_refresh_button.value

    # Get current status (this will be updated each time the button is clicked)
    server_status = check_server_health()
    container_status = check_container_status()

    # Create status display
    status_display = mo.md(f"""
    **Current Status:**
    - {server_status}
    - {container_status}

    _Click "Refresh Status" to update_
    """)

    status_display
    return container_status, server_status, status_display


@app.cell(hide_code=True)
def _(asyncio, mo, prompt_selector, run_button, run_chats_parallel):
    update_tabs = False
    mo.stop(not run_button.value)

    try:
        # Create new event loop for each run
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        task = loop.create_task(run_chats_parallel(prompt_selector.value))
        loop.run_until_complete(asyncio.wait_for(task, timeout=None))

        update_tabs = True

    except asyncio.CancelledError:
        task.cancel()
        try:
            loop.run_until_complete(task)
        except asyncio.CancelledError:
            pass
    finally:
        loop.close()
    return loop, task, update_tabs


@app.cell(hide_code=True)
def _(mo, responses, update_tabs):
    if update_tabs:
        tabs = mo.ui.tabs({result['prompt'][:40]: result["result"] for result in responses})

    tabs
    return (tabs,)


@app.cell(hide_code=True)
def _(__file__):
    import os
    from operations.blocks.blockCache import BlockCache
    from datetime import datetime

    # Get the existing BlockCache instance that's used by the application
    # The file path should match what's used in the main application
    cache_db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'block_cache.db')

    # Use the real DB file instead of in-memory for metrics display
    block_cache = BlockCache(db_path=cache_db_path, load_from_disk=True, run_on_start=True)
    return BlockCache, block_cache, cache_db_path, datetime, os


@app.cell(hide_code=True)
def _(mo):
    # Create the refresh button in its own cell
    refresh_button = mo.ui.button(label="Refresh Metrics")
    refresh_button
    return (refresh_button,)


@app.cell(hide_code=True)
def _(block_cache, datetime, mo, refresh_button):
    # This cell displays the metrics and will re-run when the button is clicked

    # Get button value to make this cell reactive to button clicks
    _ = refresh_button.value

    # Get timestamp for display
    current_time = datetime.now().strftime('%H:%M:%S')

    # Get metrics data
    metrics = block_cache.get_metrics()
    hits = metrics.get("hits", 0)
    misses_not_found = metrics.get("misses_not_found", 0)
    misses_expired = metrics.get("misses_expired", 0)
    total_misses = misses_not_found + misses_expired
    total_requests = hits + total_misses

    hit_ratio = (hits / total_requests) * 100 if total_requests > 0 else 0
    miss_not_found_ratio = (misses_not_found / total_requests) * 100 if total_requests > 0 else 0
    miss_expired_ratio = (misses_expired / total_requests) * 100 if total_requests > 0 else 0

    # Add DB path info to help with debugging
    db_path = block_cache.db_path

    # Create the metrics display
    metrics_md = f"""
    | Metric | Count | Percentage |
    | ------ | ----- | ---------- |
    | Hits | {hits} | {hit_ratio:.1f}% |
    | Misses (Not Found) | {misses_not_found} | {miss_not_found_ratio:.1f}% |
    | Misses (Expired) | {misses_expired} | {miss_expired_ratio:.1f}% |
    | Total Requests | {total_requests} | 100% |

    _Cache DB: {db_path}_  
    _Last updated: {current_time}_
    """

    # Display metrics
    mo.md(metrics_md)
    return (
        current_time,
        db_path,
        hit_ratio,
        hits,
        metrics,
        metrics_md,
        miss_expired_ratio,
        miss_not_found_ratio,
        misses_expired,
        misses_not_found,
        total_misses,
        total_requests,
    )


if __name__ == "__main__":
    app.run()
