"""CLI entry point for the AI 2D Animation Studio pipeline."""
import json

import click

from . import client


# ── Shared output helpers ──


def _print(data, as_json: bool = False):
    if as_json:
        click.echo(json.dumps(data, indent=2, default=str))
    else:
        if isinstance(data, list):
            for item in data:
                _print_item(item)
        else:
            _print_item(data)


def _print_item(item: dict):
    if not item:
        return
    if "name" in item and "id" in item:
        click.echo(f"  {item['name']:30s} {item['id']}")
    elif "title" in item and "id" in item:
        click.echo(f"  {item['title']:30s} {item['id']}")
    elif "type" in item and "id" in item:
        click.echo(f"  {item['type']:30s} {item['status']:12s} {item['id']}")
    else:
        click.echo(json.dumps(item, indent=2, default=str))


# ══════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════


@click.group()
def cli():
    """AI 2D Animation Studio pipeline CLI."""


# ── Project ──


@cli.group()
def project():
    """Manage projects."""


@project.command("list")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def project_list(as_json: bool):
    """List all projects."""
    _print(client.list_projects(), as_json=as_json)


@project.command("create")
@click.argument("name")
@click.option("--style", default="2d_anime", help="Animation style")
@click.option("--aspect-ratio", default="9:16", help="Aspect ratio (e.g. 9:16, 16:9)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def project_create(name: str, style: str, aspect_ratio: str, as_json: bool):
    """Create a new project."""
    data = client.create_project(name, style=style, aspect_ratio=aspect_ratio)
    click.echo(f"Created project: {data['id']}")
    _print(data, as_json=as_json)


@project.command("get")
@click.argument("project_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def project_get(project_id: str, as_json: bool):
    """Get project details."""
    _print(client.get_project(project_id), as_json=as_json)


@project.command("delete")
@click.argument("project_id")
def project_delete(project_id: str):
    """Delete a project."""
    client.delete_project(project_id)
    click.echo(f"Deleted project {project_id}")


# ── Story ──


@cli.group()
def story():
    """Manage story bibles."""


@story.command("generate")
@click.argument("project_id")
@click.option("--concept", help="Optional story concept/prompt")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def story_generate(project_id: str, concept: str | None, as_json: bool):
    """Generate story bible for a project."""
    data = client.generate_story(project_id, concept=concept)
    click.echo(f"Story generated: {data.get('series_name', 'N/A')}")
    _print(data, as_json=as_json)


@story.command("materialize")
@click.argument("project_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def story_materialize(project_id: str, as_json: bool):
    """Materialize story into scenes and shots."""
    data = client.materialize_story(project_id)
    click.echo(f"Materialized: {data.get('scenes', 0)} scenes, {data.get('characters', 0)} characters")
    _print(data, as_json=as_json)


# ── Export ──


@cli.group()
def export():
    """Export scenes or projects."""


@export.command("project")
@click.argument("project_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def export_project(project_id: str, as_json: bool):
    """Export all scenes and concatenate."""
    data = client.export_project(project_id)
    click.echo(f"Export dispatched: {data.get('scene_count', 0)} scenes, concat job: {data.get('concat_job_id')}")
    _print(data, as_json=as_json)


@export.command("scene")
@click.argument("scene_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def export_scene(scene_id: str, as_json: bool):
    """Export a single scene."""
    data = client.export_scene(scene_id)
    click.echo(f"Scene export dispatched: job_id={data.get('job_id')}")
    _print(data, as_json=as_json)


# ── Jobs ──


@cli.group()
def job():
    """Manage jobs."""


@job.command("list")
@click.argument("project_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def job_list(project_id: str, as_json: bool):
    """List jobs for a project."""
    _print(client.list_jobs(project_id), as_json=as_json)


@job.command("get")
@click.argument("job_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def job_get(job_id: str, as_json: bool):
    """Get job status."""
    _print(client.get_job(job_id), as_json=as_json)


@job.command("cancel")
@click.argument("project_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def job_cancel(project_id: str, as_json: bool):
    """Cancel pending jobs for a project."""
    data = client.cancel_jobs(project_id)
    click.echo(f"Cancelled {data.get('cancelled', 0)} jobs")
    _print(data, as_json=as_json)


# ── Batch ──


@cli.group()
def batch():
    """Batch generation commands."""


@batch.command("keyframes")
@click.argument("scene_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def batch_keyframes(scene_id: str, as_json: bool):
    """Generate keyframes for all shots in a scene."""
    data = client.generate_all_keyframes(scene_id)
    click.echo(f"Dispatched batch: {len(data.get('job_ids', []))} keyframe jobs")
    _print(data, as_json=as_json)


@batch.command("audio")
@click.argument("scene_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def batch_audio(scene_id: str, as_json: bool):
    """Generate audio for all shots in a scene."""
    data = client.generate_all_audio(scene_id)
    click.echo(f"Dispatched batch: {len(data.get('job_ids', []))} audio jobs")
    _print(data, as_json=as_json)


# ── Seed ──


@cli.command()
@click.argument("project_id")
@click.option("--concept", default="A lone warrior in a cyberpunk city discovers an ancient artifact",
              help="Story concept")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def seed(project_id: str, concept: str, as_json: bool):
    """Full pipeline seed: story generate → materialize."""
    click.echo("Generating story...")
    story_data = client.generate_story(project_id, concept=concept)
    click.echo(f"Story: {story_data.get('series_name', 'N/A')}")

    click.echo("Materializing scenes and shots...")
    mat_data = client.materialize_story(project_id)
    click.echo(f"Materialized: {mat_data.get('scenes', 0)} scenes")

    if as_json:
        _print({"story": story_data, "materialize": mat_data}, as_json=True)


if __name__ == "__main__":
    cli()
