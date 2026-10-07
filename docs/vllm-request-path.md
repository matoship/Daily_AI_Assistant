- What run.py, factory.py, TrackedClient and OpenAICompatibleAdapter each own
  run.py is responsible to run the program, connecting different features. It intialise the service, extract models
  factory.py owns LLM settings
  TrackedClient owns telemetry of LLM
  OpenAICompatibleAdpater owns adapter for llm that is suitable for openai and openai framed model

- What crosses the HTTP boundary

- What the vLLM API server, engine/scheduler, model executor and RTX 4090 each own.
  vLLM APi server acting as public face entrying point, it handles external communication and translate user requests.
  Engine/schedular optimise how request are boundled together to maximise throughput.

- MOdel Executor
  The Model Executor is responsible for running the actual neural network math. It acts as the bridge between the logicial scheduling decisions and the raw hardware.

- 4090
  4090 is the hardware that provides computing power and memory resource.
