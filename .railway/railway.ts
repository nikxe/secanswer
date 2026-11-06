import { defineRailway, github, image, preserve, project, service } from "railway/iac";

export default defineRailway(() => {
  const ollama = service("ollama", {
    source: image("ollama/ollama"),
    build: { buildEnvironment: "V3", builder: "RAILPACK" },
    replicas: { "iad": 1 },
    deploy: { startCommand: "sh -c 'ollama serve & sleep 10 && ollama pull nomic-embed-text && wait'" },
  });
  const secanswer = service("secanswer", {
    source: github("nikxe/secanswer", { branch: "main", checkSuites: false, rootDirectory: "/backend" }),
    build: { buildEnvironment: "V3", builder: "RAILPACK" },
    replicas: { "iad": 1 },
    deploy: { ipv6EgressEnabled: true },
    env: { DATABASE_URL: preserve(), EMBEDDING_API_KEY: preserve(), EMBEDDING_BASE_URL: preserve(), EMBEDDING_DIM: preserve(), EMBEDDING_MODEL: preserve(), LLM_API_KEY: preserve(), LLM_BASE_URL: preserve(), LLM_MODEL: preserve(), PYTHONUNBUFFERED: preserve() },
  });

  return project("graceful-youth", {
    variables: { managed: true },
    resources: [ollama, secanswer],
  });
});
