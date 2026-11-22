# Test deletion in OpenAI Agents

The application stores two messages in a real SQLiteSession. Its answer route reads those messages. The fixed deletion removes only the selected customer's row; the retained message stays readable.

## Run the example

Use Python 3.11 or later in a fresh checkout. The fixture starts a loopback HTTP service and creates new test credentials for each lane.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python demo.py
setrya replay example-results/broken
setrya replay example-results/fixed
```

The first replay exits 1. The deletion route acknowledged the request while the duty agent could still recover `Harbor-17`. The fixed replay exits 0. The same agent loses the depot code and can still answer “Thursday” to the dispatch question. You can replay either bundle after shutting down the app. This example tests deletion without a background worker.

## Connect your application

Generate the same starting case with `setrya init --stack openai-agents --output my-case`. In `case.yml`, set your fixture’s origin, separate read and erase credentials, subject, questions and scoped store keys. The sample’s `storage.py` shows the app-side operation that changes between the two runs. Keep the generated inspector and scanner when your store uses the same layout. Run `setrya doctor --case my-case/case.yml`, then `setrya run my-case/case.yml --mode deletion --output my-receipt`.

[Setrya](https://github.com/davidahma/setrya) · [Case format](https://github.com/davidahma/setrya/blob/v1.2.0/docs/http-cases.md)
