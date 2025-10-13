from watchfiles import awatch
import asyncio
import inspect

async def handle_realtime_changes(prompts_path, function):
    """
    Watch a folder for real-time changes and run a callback when they occur.
    `function` can be sync or async.
    """
    folder_to_watch = prompts_path
    print(f"👀 Watching folder: {folder_to_watch} for changes...")

    # Watch the folder recursively for any change
    async for changes in awatch(folder_to_watch):
        print("🔄 Detected change in watched folder!")
        for change_type, file_path in changes:
            print(f"  • {change_type.name} → {file_path}")

        # Run the provided function (support both sync and async)
        try:
            if inspect.iscoroutinefunction(function):
                await function()
            else:
                # Run sync function in a thread to avoid blocking event loop
                await asyncio.to_thread(function)
        except Exception as e:
            print(f"⚠️ Error while running change handler: {e}")
