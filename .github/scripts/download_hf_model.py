import os
import shutil
import sys
import time
import urllib.error
import urllib.request

from huggingface_hub import hf_hub_download
from huggingface_hub.utils import HfHubHTTPError


def is_zip(path: str) -> bool:
    with open(path, "rb") as handle:
        return handle.read(2) == b"PK"


def validate_zip(path: str) -> None:
    if not is_zip(path):
        raise ValueError(f"{path} does not look like a zip archive")


def download_direct(url: str, dest: str) -> None:
    print(f"Trying direct download: {url}")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "fruitbox-ci/1.0"},
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        data = response.read()
    if data[:2] != b"PK":
        raise ValueError("response is not a zip archive")
    with open(dest, "wb") as handle:
        handle.write(data)


def download_from_hf(repo: str, revision: str, filename: str, token: str | None) -> str:
    print(f"Downloading {filename} from Hugging Face ({repo}@{revision})")
    last_error: Exception | None = None
    for attempt in range(5):
        try:
            return hf_hub_download(
                repo_id=repo,
                filename=filename,
                revision=revision,
                token=token,
            )
        except HfHubHTTPError as exc:
            last_error = exc
            status = exc.response.status_code if exc.response is not None else None
            if status == 429 and attempt < 4:
                wait = 15 * (2**attempt)
                print(f"Hugging Face rate limited (429), retrying in {wait}s...")
                time.sleep(wait)
                continue
            raise
    raise last_error  # type: ignore[misc]


def fallback_sources(filename: str) -> list[str]:
    sources: list[str] = []

    mirror = os.environ.get("FRUITBOX_MODEL_MIRROR_URL")
    if mirror:
        sources.append(mirror)

    gh_repo = os.environ.get("GITHUB_REPOSITORY")
    if gh_repo:
        sources.append(
            f"https://github.com/{gh_repo}/releases/latest/download/{filename}"
        )

    hf_repo = os.environ.get("HF_MODEL_REPO")
    hf_revision = os.environ.get("HF_MODEL_REVISION")
    if hf_repo and hf_revision:
        sources.append(
            f"https://huggingface.co/{hf_repo}/resolve/{hf_revision}/{filename}"
        )

    return sources


def main() -> None:
    repo = os.environ["HF_MODEL_REPO"]
    revision = os.environ["HF_MODEL_REVISION"]
    filename = os.environ["HF_MODEL_FILE"]
    token = os.environ.get("HF_TOKEN") or None
    dest = os.path.join(os.getcwd(), filename)

    if os.path.isfile(dest) and is_zip(dest):
        print(f"Using existing {filename} ({os.path.getsize(dest)} bytes)")
        return

    errors: list[str] = []

    try:
        cached_path = download_from_hf(repo, revision, filename, token)
        shutil.copy2(cached_path, dest)
        validate_zip(dest)
        print(f"Downloaded {filename} from Hugging Face ({os.path.getsize(dest)} bytes)")
        return
    except Exception as exc:
        errors.append(f"Hugging Face: {exc}")

    for url in fallback_sources(filename):
        try:
            download_direct(url, dest)
            validate_zip(dest)
            print(f"Downloaded {filename} from fallback ({os.path.getsize(dest)} bytes)")
            return
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as exc:
            errors.append(f"{url}: {exc}")

    print("All model download sources failed:", file=sys.stderr)
    for error in errors:
        print(f"  - {error}", file=sys.stderr)
    print(
        "Optional mitigations: set HF_TOKEN, FRUITBOX_MODEL_MIRROR_URL, "
        "or publish fruitbox_ppo_final.zip to GitHub Releases.",
        file=sys.stderr,
    )
    raise SystemExit(1)


if __name__ == "__main__":
    main()
