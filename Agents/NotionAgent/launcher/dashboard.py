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
    import aiohttp
    import json

    from tz_common.logs import log, LogLevel

    from chat import chat

    nest_asyncio.apply()
    log.set_log_level(LogLevel.FLOW)
    log.set_file_log_level(LogLevel.FLOW)

    return (
        ChatPromptTemplate,
        LogLevel,
        RunnableParallel,
        aiohttp,
        asyncio,
        chat,
        json,
        log,
        nest_asyncio,
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

    # Status will be updated automatically - no need for separate text components

    execution_controls = mo.hstack([run_button, mode_switch], 
                                 widths=[120, 200], gap=1)

    # Auto-refresh timer - fixed 5 seconds (no UI component)
    refresh_timer = mo.ui.refresh(default_interval="5s")

    return (
        execution_controls,
        mode_switch,
        prompt_selector,
        refresh_timer,
        run_button,
    )


@app.cell(hide_code=True)
def _(mo):
    # Create Docker buttons in their own cell (like refresh button)
    launch_container_button = mo.ui.button(label="Launch Container")
    stop_container_button = mo.ui.button(label="Stop Container")
    
    docker_controls = mo.hstack([launch_container_button, stop_container_button],
                               widths=[140, 200], gap=1)
    
    return launch_container_button, stop_container_button, docker_controls


@app.cell(hide_code=True)
def _(execution_controls, prompt_selector, docker_controls, mo):
    # Main layout
    main_layout = mo.vstack([
        execution_controls,
        prompt_selector,
        mo.md("**Docker Container Management**"),
        docker_controls
    ])

    main_layout
    return (main_layout,)


@app.cell(hide_code=True)
def _(launch_container_button, stop_container_button, mo, log):
    # Debug display for button states - right below buttons
    log.flow("Button states check", f"Launch: {launch_container_button.value}, Stop: {stop_container_button.value}")
    
    debug_text = f"**Debug:** Launch: {launch_container_button.value}, Stop: {stop_container_button.value}"
    mo.md(debug_text)
    return (debug_text,)


@app.cell(hide_code=True)
def _(
    check_container_status,
    check_server_health,
    launch_result,
    mo,
    refresh_timer,
    stop_result,
):
    # This cell will refresh automatically due to refresh_timer dependency
    _ = refresh_timer.value  # Make this cell reactive to timer

    # Get current status
    server_status = check_server_health()
    container_status = check_container_status()

    # Show button results if any
    button_results = []
    if launch_result:
        button_results.append(f"Launch: {launch_result}")
    if stop_result:
        button_results.append(f"Stop: {stop_result}")

    button_results_text = " | ".join(button_results) if button_results else ""

    # Create status display
    status_text = f"**Status:** {server_status} | {container_status}"

    if button_results_text:
        status_text += f"\n\n**Last Action:** {button_results_text}"

    status_display = mo.md(status_text)

    # Display both timer and status
    mo.hstack([status_display, refresh_timer])
    return (
        button_results,
        button_results_text,
        container_status,
        refresh_timer,
        server_status,
        status_display,
        status_text,
    )


@app.cell(hide_code=True)
def _(aiohttp, asyncio, chat, log, mo, responses, run_button, time):
    mo.stop(run_button.value is None, mo.md("**Click button to run chats.**"))

    async def send_to_server(prompt: str, base_url: str = "http://localhost:8000") -> str:
        """Send request to REST server"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{base_url}/api/v1/process", 
                    json={"input": prompt},
                    timeout=aiohttp.ClientTimeout(total=300)  # 5 minute timeout
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("result", "No result returned")
                    else:
                        error_text = await response.text()
                        return f"Server error ({response.status}): {error_text}"
        except aiohttp.ClientError as e:
            return f"Connection error: {str(e)}"
        except asyncio.TimeoutError:
            return "Request timed out (5 minutes)"
        except Exception as e:
            return f"Unexpected error: {str(e)}"

    async def run_chat(option, use_server_mode=False):
        log.flow(f"Starting chat for {option}", f"Server mode: {use_server_mode}")
        start_time = time.time()

        if use_server_mode:
            result = await send_to_server(option)
        else:
            result = await asyncio.to_thread(chat, loop=False, user_prompt=option)

        end_time = time.time()
        execution_time = end_time - start_time
        return {
            'prompt': option,
            'result': result,
            'execution_time': execution_time,
            'mode': 'server' if use_server_mode else 'local'
        }

    async def run_chats_parallel(options, use_server_mode=False):
        responses.clear()
        tasks = [asyncio.create_task(run_chat(option, use_server_mode)) for option in options]

        # Use as_completed to handle results as they arrive
        for completed_task in asyncio.as_completed(tasks):
            try:
                result = await completed_task
                responses.append(result)
                mode_text = f"({result['mode']} mode)"
                log.user(f"Completed task {mode_text}:", {result['prompt']})
                log.debug(f"Took {result['execution_time']:.2f} seconds")
            except Exception as e:
                log.error("Task failed", str(e))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    return run_chat, run_chats_parallel, send_to_server


@app.cell(hide_code=True)
def _():
    from docker_manager import DockerManager
    
    # Initialize Docker manager
    docker_manager = DockerManager()
    
    return docker_manager,


@app.cell(hide_code=True)
def _(launch_container_button, stop_container_button, docker_manager, log):
    # Handle button clicks - this cell will re-run when buttons are clicked
    launch_result = None
    stop_result = None

    if launch_container_button.value is not None:
        log.flow("Launch button clicked", f"Button value: {launch_container_button.value}")
        launch_result = docker_manager.launch_container()
        log.flow("Launch result", launch_result)

    if stop_container_button.value is not None:
        log.flow("Stop button clicked", f"Button value: {stop_container_button.value}")
        stop_result = docker_manager.stop_container()
        log.flow("Stop result", stop_result)
    
    return launch_result, stop_result


@app.cell(hide_code=True)
def _(docker_manager):
    # Status checking functions using DockerManager
    def check_server_health():
        return docker_manager.check_server_health()

    def check_container_status():
        return docker_manager.check_container_status()
        
    return check_container_status, check_server_health


@app.cell(hide_code=True)
def _(
    asyncio,
    mo,
    mode_switch,
    prompt_selector,
    run_button,
    run_chats_parallel,
):
    update_tabs = False
    mo.stop(not run_button.value)

    try:
        # Create new event loop for each run
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Get the server mode setting
        use_server_mode = mode_switch.value

        task = loop.create_task(run_chats_parallel(prompt_selector.value, use_server_mode))
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
    return loop, task, update_tabs, use_server_mode


@app.cell(hide_code=True)
def _(mo, responses, update_tabs):
    if update_tabs:
        # Create tabs with mode indicator and execution time
        tab_data = {}
        for result in responses:
            mode_indicator = "🖥️" if result.get('mode') == 'server' else "💻"
            time_str = f" ({result.get('execution_time', 0):.1f}s)"
            tab_title = f"{mode_indicator} {result['prompt'][:35]}{time_str}"
            tab_data[tab_title] = result["result"]

        tabs = mo.ui.tabs(tab_data)

    tabs
    return mode_indicator, result, tab_data, tab_title, tabs, time_str


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
