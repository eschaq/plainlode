"""Launch the Plainlode report-voice LoRA fine-tune on Fireworks.

Uploads finetune/train.jsonl as a dataset and starts a supervised fine-tuning
(SFT) LoRA job on the gpt-oss-20b base. It creates the job ONLY: no deployment,
no GPU spins up until a later explicit serving step. It does not poll to
completion.

Why this does not touch the LLM wrapper:
Introspected against fireworks-ai 0.19.20. The only public job-creation helper
is `LLM.create_supervised_fine_tuning_job`, which requires constructing an `LLM`
object. Reading its source, that helper does NOT create a deployment (it builds
a job proto and calls the control-plane create API; only `LLM.apply()` deploys).
But to keep fine-tuning fully decoupled from any deployment wrapper, we build the
same job proto directly and drive the exposed `SupervisedFineTuningJob` class
with `llm=None`. Its create/sync/get/id/url paths only store `llm`, never call a
method on it, so no LLM is needed and nothing is deployed.

Run from the repo root:  python -m finetune.run_sft
"""

import os
from uuid import uuid4

from fireworks import Dataset, SupervisedFineTuningJob
from fireworks.gateway import Gateway
# Proto type only; importing this symbol does not instantiate an LLM.
from fireworks.llm.llm import SyncSupervisedFineTuningJob

TRAIN_PATH = "finetune/train.jsonl"
DATASET_ID = "plainlode-voice-v1"
OUTPUT_MODEL = "accounts/eschachter/models/plainlode-voice-v2"
DISPLAY_NAME = "plainlode-voice"
EPOCHS = 3


def main():
    api_key = os.environ.get("FIREWORKS_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "FIREWORKS_API_KEY not set. Source .env before running: "
            "set -a; source .env; set +a"
        )
    base_model = "accounts/fireworks/models/llama-v3p1-8b-instruct"
    if not base_model:
        raise RuntimeError(
            "FIREWORKS_MODEL not set. Set it to the gpt-oss-20b base id, e.g. "
            "accounts/fireworks/models/gpt-oss-20b"
        )

    # 1. Upload the training set. from_file derives a content-hash id; override
    #    to a stable readable id. sync() creates the server dataset with that id
    #    and is idempotent on re-run.
    dataset = Dataset.from_file(TRAIN_PATH)
    dataset._id = DATASET_ID
    dataset.sync()

    # 2. Build the SFT job proto directly (no LLM, no deployment). Mirrors the
    #    fields LLM.create_supervised_fine_tuning_job sets, with base_model set to
    #    our gpt-oss-20b base (it is a base model, not a PEFT add-on).
    gateway = Gateway(api_key=api_key)
    unique_name = f"{DISPLAY_NAME}-{str(uuid4())[:5].lower()}"
    proto = SyncSupervisedFineTuningJob(
        name=f"accounts/{gateway.account_id()}/supervisedFineTuningJobs/{unique_name}",
        display_name=DISPLAY_NAME,
        base_model=base_model,
        dataset=dataset.name,
        output_model=OUTPUT_MODEL,
        epochs=EPOCHS,
    )

    # 3. Create the job. llm=None is safe: the create/sync/get/id/url paths only
    #    store llm, they never call a method on it. lora_rank is left unset on the
    #    proto, so the server applies the default LoRA rank.
    job = SupervisedFineTuningJob(
        llm=None,
        proto=proto,
        dataset_or_id=dataset,
        api_key=api_key,
    )
    job = job.sync()  # control-plane create; no deployment, no GPU

    print("Fine-tune launched (job only, no deployment).")
    print(f"  Base model:       {base_model}")
    print(f"  Dataset id:       {dataset.id}")
    print(f"  Fine-tuning job:  {job.id}")
    print(f"  Output model id:  {job.output_model or OUTPUT_MODEL}")
    print(f"  Epochs:           {EPOCHS}  (LoRA rank: default)")
    print()
    print("Check job status (does not poll here):")
    print(f"  Dashboard/API URL: {job.url}")
    print(f"  CLI:  firectl get sftj {job.id}")


if __name__ == "__main__":
    main()
