import json
import os
import logging
import re
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.theme import Theme
from rich.table import Table
from rich.text import Text

logging.basicConfig(filename='todo_list.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
console = Console()

FILE_NAME = 'todo_list.json'
MAX_DESCRIPTION_LENGTH = 200
FORBIDDEN_CHARACTERS = re.compile(r'[<>:"/\\|?*\x00-\x1F]')
FORBIDDEN_URL_PATTERN = re.compile(r'http(s)?://')
FORBIDDEN_WORDS = [
    'sex',
    'violence',
    'drugs',
    'hate',
    'abuse',
    'illegal',
    'adult',
    'explicit',
    'harassment',
    'discrimination',
    'extremism']

# Define themes
THEMES = {
    "dracula": Theme({
        "panel.border": "red",
        "table.border": "cyan",
        "table.title": "bold yellow",
        "text": "white"
    }),
    "monokai": Theme({
        "panel.border": "magenta",
        "table.border": "green",
        "table.title": "bold yellow",
        "text": "white"
    }),
    "solarized": Theme({
        "panel.border": "blue",
        "table.border": "green",
        "table.title": "bold cyan",
        "text": "black"
    })
}

class InvalidGroupNameError(Exception):
    pass


class InvalidDescriptionError(Exception):
    pass


class TaskManager:
    def __init__(self, file_name=FILE_NAME):
        self.file_name = file_name
        self.tasks = self.load_data()

    def load_data(self):
        try:
            if os.path.exists(self.file_name):
                with open(self.file_name, 'r') as file:
                    return json.load(file)
            return {}
        except json.JSONDecodeError:
            console.print(
                "[red]Error: The JSON file is corrupted or empty. Creating a new one.[/red]")
            return {}
        except Exception as e:
            console.print(
                f"[red]An error occurred while loading data: {e}[/red]")
            console.print(
                "[red]Please check the log file 'todo_list.log' for more details.[/red]")
            logger.error(f"An error occurred while loading data: {e}")
            return {}

    def save_data(self):
        try:
            with open(self.file_name, 'w') as file:
                json.dump(self.tasks, file, indent=4)
        except IOError as e:
            console.print(f"[red]Error saving data: {e}[/red]")
            console.print(
                "[red]Please check the log file 'todo_list.log' for more details.[/red]")
            logger.error(f"Error saving data: {e}")

    def reset_data(self):
        try:
            if os.path.exists(self.file_name):
                if Prompt.ask(
                    "Are you sure you want to reset all data? (yes/no)",
                    choices=[
                        "yes",
                        "no"]) == "yes":
                    os.remove(self.file_name)
                    console.print(
                        "[yellow]All data has been reset and file removed.[/yellow]")
                else:
                    console.print("[yellow]Data reset canceled.[/yellow]")
            else:
                console.print("[red]No data file found to reset.[/red]")
        except IOError as e:
            console.print(f"[red]Error resetting data: {e}[/red]")
            console.print(
                "[red]Please check the log file 'todo_list.log' for more details.[/red]")
            logger.error(f"Error resetting data: {e}")

    def add_tasks(self, group_name, descriptions):
        if not self.is_valid_group_name(group_name):
            raise InvalidGroupNameError(
                "Invalid group name. Please avoid special characters and inappropriate words.")

        if group_name not in self.tasks:
            self.tasks[group_name] = []

        start_id = max((task.get('id', 0)
                       for task in self.tasks[group_name]), default=0) + 1

        for i, description in enumerate(descriptions, start=start_id):
            if self.is_valid_description(description):
                self.tasks[group_name].append(
                    {"id": i, "description": description, "completed": False})
            else:
                raise InvalidDescriptionError(
                    f"Invalid task description: {description}")

        self.save_data()
        logger.info(
            f"Added tasks to group '{group_name}': {', '.join(descriptions)}")
        console.print(
            f"[green]Tasks added to group '{group_name}':[/green] {', '.join(descriptions)}")

    def edit_task(self, group_name, task_id, new_description):
        if not self.is_valid_description(new_description):
            raise InvalidDescriptionError(
                "Invalid task description. Please avoid special characters and inappropriate words.")

        if group_name in self.tasks:
            for task in self.tasks[group_name]:
                if task["id"] == task_id:
                    task["description"] = new_description
                    self.save_data()
                    logger.info(
                        f"Edited task in group '{group_name}': ID {task_id} -> {new_description}")
                    console.print(
                        f"[yellow]Task updated in group '{group_name}':[/yellow] ID {task_id} -> '{new_description}'")
                    return
            console.print("[red]Task not found in the group.[/red]")
        else:
            console.print("[red]Invalid group name.[/red]")

    def mark_tasks_complete(self, group_name, task_ids):
        if group_name in self.tasks:
            ids = [int(id.strip()) for id in task_ids.split(',')]
            for task in self.tasks[group_name]:
                if task["id"] in ids:
                    task["completed"] = True
            self.save_data()
            logger.info(
                f"Marked tasks in group '{group_name}' as complete: {', '.join(map(str, ids))}")
            console.print(
                f"[blue]Tasks marked as complete in group '{group_name}':[/blue] {', '.join(map(str, ids))}")

            if all(task["completed"] for task in self.tasks[group_name]):
                if Prompt.ask(
                    f"All tasks in group '{group_name}' are complete. Do you want to delete the group? (yes/no)",
                    choices=[
                        "yes",
                        "no"]) == "yes":
                    del self.tasks[group_name]
                    self.save_data()
                    logger.info(
                        f"Deleted group '{group_name}' after all tasks were completed")
                    console.print(f"[red]Group '{group_name}' deleted.[/red]")
        else:
            console.print("[red]Invalid group name.[/red]")

    def delete_tasks(self, group_name, task_ids):
        if group_name in self.tasks:
            ids = [int(id.strip())
                   for id in task_ids.split(',') if id.strip().isdigit()]
            self.tasks[group_name] = [
                task for task in self.tasks[group_name] if task.get("id") not in ids]

            if not self.tasks[group_name]:
                if Prompt.ask(
                    f"Group '{group_name}' is now empty. Do you want to delete the group? (yes/no)",
                    choices=[
                        "yes",
                        "no"]) == "yes":
                    del self.tasks[group_name]
                    console.print(f"[red]Group '{group_name}' deleted.[/red]")

            self.save_data()
            logger.info(
                f"Deleted tasks from group '{group_name}': {', '.join(map(str, ids))}")
            console.print(
                f"[red]Tasks deleted from group '{group_name}':[/red] {', '.join(map(str, ids))}")
        else:
            console.print("[red]Invalid group name.[/red]")

    def is_valid_group_name(self, name):
        return not (FORBIDDEN_CHARACTERS.search(name) or any(
            word in name.lower() for word in FORBIDDEN_WORDS))

    def is_valid_description(self, description):
        return len(description) <= MAX_DESCRIPTION_LENGTH and not FORBIDDEN_URL_PATTERN.search(
            description)


class UserInterface:
    def __init__(self, task_manager):
        self.task_manager = task_manager
        self.console = Console(theme=THEMES.get("dracula"))
        
    def choose_theme(self):
        try:
            theme_choice = Prompt.ask(
                "Choose a theme dracula/monokai/solarized").strip().lower()
            if theme_choice in THEMES:
                self.console = Console(theme=THEMES[theme_choice])
                console.print(f"[green]Theme changed to {theme_choice}[/green]")
            else:
                console.print("[red]Invalid theme choice. Please choose from dracula, monokai, solarized.[/red]")
        except Exception as e:
            console.print(
                f"[red]An error occurred while changing theme: {e}[/red]")
            console.print(
                "[red]Please check the log file 'todo_list.log' for more details.[/red]")
            logger.error(f"An error occurred while changing theme: {e}")

    def display_tasks(self):
        try:
            for group_name, task_list in self.task_manager.tasks.items():
                table = Table(
                    title=f"[bold cyan]Group: {group_name}[/bold cyan]",
                    title_justify="center",
                    border_style="blue",
                    padding=(
                        1,
                        2))
                table.add_column("ID", style="cyan", justify="center")
                table.add_column("Description", style="magenta")
                table.add_column("Status", justify="center", style="green")

                for task in task_list:
                    status = "✓" if task["completed"] else "✗"
                    table.add_row(str(task['id']), task['description'], status)

                console.print(
                    Panel(
                        table,
                        title=f"[bold yellow]Tasks in group '{group_name}'[/bold yellow]",
                        title_align="left",
                        border_style="bold yellow"))
        except Exception as e:
            console.print(
                f"[red]An error occurred while displaying tasks: {e}[/red]")
            console.print(
                "[red]Please check the log file 'todo_list.log' for more details.[/red]")
            logger.error(f"An error occurred while displaying tasks: {e}")

    def handle_add_task(self):
        try:
            group_name = Prompt.ask("Enter the group name for these tasks")
            if not self.task_manager.is_valid_group_name(group_name):
                console.print(
                    "[red]Invalid group name. Please avoid special characters and inappropriate words.[/red]")
                return

            descriptions = []
            while True:
                description = Prompt.ask(
                    "Enter task description (or type 'done' to finish)")
                if description.lower() == 'done':
                    break
                if self.task_manager.is_valid_description(description):
                    descriptions.append(description)
                else:
                    console.print(
                        f"[red]Invalid task description: {description}[/red]")

            if descriptions:
                self.task_manager.add_tasks(group_name, descriptions)
        except Exception as e:
            console.print(
                f"[red]An error occurred while adding tasks: {e}[/red]")
            console.print(
                "[red]Please check the log file 'todo_list.log' for more details.[/red]")
            logger.error(f"An error occurred while adding tasks: {e}")
            
    
    
            

    def handle_edit_task(self):
        try:
            group_name = Prompt.ask("Enter the group name")
            task_id = int(Prompt.ask("Enter task ID"))
            new_description = Prompt.ask("Enter new task description")
            self.task_manager.edit_task(group_name, task_id, new_description)
        except Exception as e:
            console.print(
                f"[red]An error occurred while editing tasks: {e}[/red]")
            console.print(
                "[red]Please check the log file 'todo_list.log' for more details.[/red]")
            logger.error(f"An error occurred while editing tasks: {e}")

    def handle_mark_complete(self):
        try:
            group_name = Prompt.ask("Enter the group name")
            task_ids = Prompt.ask(
                "Enter task IDs to mark as complete (comma-separated)")
            self.task_manager.mark_tasks_complete(group_name, task_ids)
        except Exception as e:
            console.print(
                f"[red]An error occurred while marking tasks as complete: {e}[/red]")
            console.print(
                "[red]Please check the log file 'todo_list.log' for more details.[/red]")
            logger.error(
                f"An error occurred while marking tasks as complete: {e}")

    def handle_delete_task(self):
        try:
            group_name = Prompt.ask("Enter the group name")
            task_ids = Prompt.ask("Enter task IDs to delete (comma-separated)")
            self.task_manager.delete_tasks(group_name, task_ids)
        except Exception as e:
            console.print(
                f"[red]An error occurred while deleting tasks: {e}[/red]")
            console.print(
                "[red]Please check the log file 'todo_list.log' for more details.[/red]")
            logger.error(f"An error occurred while deleting tasks: {e}")

    def display_menu(self):
        menu_table = Table(
            title="[bold magenta]Todo List Menu[/bold magenta]",
            title_justify="left",
            border_style="green")
        menu_table.add_column("Option", justify="center", style="cyan")
        menu_table.add_column("Action", style="magenta")

        menu_table.add_row("1", "Add Task")
        menu_table.add_row("2", "Edit Task")
        menu_table.add_row("3", "Mark Task Complete")
        menu_table.add_row("4", "Delete Task")
        menu_table.add_row("5", "Display Tasks")
        menu_table.add_row("6", "Reset Data")
        menu_table.add_row("7", "Change Theme")
        menu_table.add_row("8", "Exit")

        console.print(Panel(menu_table, border_style="bold blue"))

    def handle_choice(self, choice):
        if choice == "1":
            self.handle_add_task()
        elif choice == "2":
            self.handle_edit_task()
        elif choice == "3":
            self.handle_mark_complete()
        elif choice == "4":
            self.handle_delete_task()
        elif choice == "5":
            self.display_tasks()
        elif choice == "6":
            self.task_manager.reset_data()
            return self.task_manager.load_data()  # Reload data after reset
        elif choice == "7":
            self.choose_theme()
        elif choice == "8":
            console.print("[green]Exiting program...[/green]")
            return None
        else:
            console.print(
                "[red]Invalid choice. Please enter a number between 1 and 7.[/red]")

        return self.task_manager.tasks


def main():
    task_manager = TaskManager()
    ui = UserInterface(task_manager)

    while True:
        try:
            ui.display_menu()
            choice = Prompt.ask("Choose an option [1/2/3/4/5/6/7]")
            task_manager.tasks = ui.handle_choice(choice)
            if task_manager.tasks is None:
                break
        except Exception as e:
            console.print(f"[red]An unexpected error occurred: {e}[/red]")
            console.print(
                "[red]Please check the log file 'todo_list.log' for more details.[/red]")
            logger.error(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
