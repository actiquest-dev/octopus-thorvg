/**
 * Gemini Live API Utilities
 * Based on multimodalLiveApi.ts - converted to JavaScript
 */

// Response type constants
const MultimodalLiveResponseType = {
  TEXT: "TEXT",
  AUDIO: "AUDIO",
  SETUP_COMPLETE: "SETUP COMPLETE",
  INTERRUPTED: "INTERRUPTED",
  TURN_COMPLETE: "TURN COMPLETE",
  TOOL_CALL: "TOOL_CALL",
  ERROR: "ERROR",
  INPUT_TRANSCRIPTION: "INPUT_TRANSCRIPTION",
  OUTPUT_TRANSCRIPTION: "OUTPUT_TRANSCRIPTION",
};

/**
 * Parses response messages from the Gemini Live API
 */
class MultimodalLiveResponseMessage {
  constructor(data) {
    this.data = "";
    this.type = "";
    this.endOfTurn = false;

    console.log("raw message data: ", data);
    this.endOfTurn = data?.serverContent?.turnComplete;

    const parts = data?.serverContent?.modelTurn?.parts;

    try {
      if (data?.setupComplete) {
        console.log("🏁 SETUP COMPLETE response", data);
        this.type = MultimodalLiveResponseType.SETUP_COMPLETE;
      } else if (data?.serverContent?.turnComplete) {
        console.log("🏁 TURN COMPLETE response");
        this.type = MultimodalLiveResponseType.TURN_COMPLETE;
      } else if (data?.serverContent?.interrupted) {
        console.log("🗣️ INTERRUPTED response");
        this.type = MultimodalLiveResponseType.INTERRUPTED;
      } else if (data?.serverContent?.inputTranscription) {
        console.log(
          "📝 INPUT TRANSCRIPTION:",
          data.serverContent.inputTranscription
        );
        this.type = MultimodalLiveResponseType.INPUT_TRANSCRIPTION;
        this.data = {
          text: data.serverContent.inputTranscription.text || "",
          finished: data.serverContent.inputTranscription.finished || false,
        };
      } else if (data?.serverContent?.outputTranscription) {
        console.log(
          "📝 OUTPUT TRANSCRIPTION:",
          data.serverContent.outputTranscription
        );
        this.type = MultimodalLiveResponseType.OUTPUT_TRANSCRIPTION;
        this.data = {
          text: data.serverContent.outputTranscription.text || "",
          finished: data.serverContent.outputTranscription.finished || false,
        };
      } else if (
        data?.toolCall ||
        data?.toolCalls ||
        data?.serverContent?.toolCall ||
        data?.serverContent?.toolCalls
      ) {
        const tc =
          data?.toolCall ||
          data?.toolCalls ||
          data?.serverContent?.toolCall ||
          data?.serverContent?.toolCalls;
        console.log("🎯 🛠️ TOOL CALL response", tc);
        this.type = MultimodalLiveResponseType.TOOL_CALL;
        this.data = tc;
      } else if (parts?.length && parts[0].text) {
        console.log("💬 TEXT response", parts[0].text);
        this.data = parts[0].text;
        this.type = MultimodalLiveResponseType.TEXT;
      } else if (parts?.length && parts[0].inlineData) {
        console.log("🔊 AUDIO response");
        this.data = parts[0].inlineData.data;
        this.type = MultimodalLiveResponseType.AUDIO;
      }
    } catch {
      console.log("⚠️ Error parsing response data: ", data);
    }
  }
}

/**
 * Function call definition for tool use
 */
class FunctionCallDefinition {
  constructor(name, description, parameters, requiredParameters) {
    this.name = name;
    this.description = description;
    this.parameters = parameters;
    this.requiredParameters = requiredParameters;
  }

  functionToCall(parameters) {
    console.log("▶️Default function call");
  }

  getDefinition() {
    const params = { ...this.parameters };
    if (this.requiredParameters && this.requiredParameters.length > 0) {
      params.required = this.requiredParameters;
    }
    // Remove empty properties object — Vertex AI rejects it
    if (params.properties && Object.keys(params.properties).length === 0) {
      delete params.properties;
    }
    const definition = {
      name: this.name,
      description: this.description,
      parameters: params,
    };
    console.log("created FunctionDefinition: ", definition);
    return definition;
  }

  async runFunction(parameters) {
    console.log(
      `⚡ Running ${this.name} function with parameters: ${JSON.stringify(
        parameters
      )}`
    );
    return await this.functionToCall(parameters);
  }
}

/**
 * Main Gemini Live API client
 */
class GeminiLiveAPI {
  constructor(proxyUrl, projectId, model) {
    this.proxyUrl = proxyUrl;
    this.projectId = projectId;
    this.model = model;
    this.modelUri = `projects/${this.projectId}/locations/global/publishers/google/models/${this.model}`;

    this.responseModalities = ["AUDIO"];
    this.systemInstructions = "";
    this.googleGrounding = false;
    this.enableAffectiveDialog = false; // Default affective dialog
    this.voiceName = "Puck"; // Default voice
    this.temperature = 1.0; // Default temperature
    this.proactivity = { proactiveAudio: false }; // Proactivity config
    this.inputAudioTranscription = false;
    this.outputAudioTranscription = false;
    this.enableFunctionCalls = false;
    this.functions = [];
    this.functionsMap = {};
    this.previousImage = null;
    this.totalBytesSent = 0;

    // Automatic activity detection settings with defaults
    this.automaticActivityDetection = {
      disabled: false,
      silence_duration_ms: 2000,
      prefix_padding_ms: 500,
      end_of_speech_sensitivity: "END_SENSITIVITY_UNSPECIFIED",
      start_of_speech_sensitivity: "START_SENSITIVITY_UNSPECIFIED",
    };

    this.activityHandling = "ACTIVITY_HANDLING_UNSPECIFIED";

    // Use Vertex AI endpoint (regional) with service account Bearer token
    this.location = "us-central1";
    this.apiHost = `${this.location}-aiplatform.googleapis.com`;
    this.serviceUrl = `wss://${this.apiHost}/ws/google.cloud.aiplatform.v1beta1.LlmBidiService/BidiGenerateContent`;

    this.connected = false;
    this.webSocket = null;
    this.lastSetupMessage = null; // Store the last setup message

    // Default callbacks
    this.onReceiveResponse = (message) => {
      console.log("Default message received callback", message);
    };

    this.onConnectionStarted = () => {
      console.log("Default onConnectionStarted");
    };

    this.onErrorMessage = (message) => {
      alert(message);
      this.connected = false;
    };

    console.log("Created Gemini Live API object: ", this);
  }

  setProjectId(projectId) {
    this.projectId = projectId;
    this.modelUri = `projects/${this.projectId}/locations/global/publishers/google/models/${this.model}`;
  }

  setApiKey(apiKey) {
    this.apiKey = apiKey;
    // Update serviceUrl to include API key for Gemini API
    if (apiKey) {
      this.serviceUrl = `wss://${this.apiHost}/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key=${apiKey}&alt=ws`;
      console.log("🔑 API key set, serviceUrl updated");
    }
  }

  setSystemInstructions(newSystemInstructions) {
    console.log("setting system instructions: ", newSystemInstructions);
    this.systemInstructions = newSystemInstructions;
  }

  setGoogleGrounding(newGoogleGrounding) {
    console.log("setting google grounding: ", newGoogleGrounding);
    this.googleGrounding = newGoogleGrounding;
  }

  setResponseModalities(modalities) {
    this.responseModalities = modalities;
  }

  setVoice(voiceName) {
    console.log("setting voice: ", voiceName);
    this.voiceName = voiceName;
  }

  setProactivity(proactivity) {
    console.log("setting proactivity: ", proactivity);
    this.proactivity = proactivity;
  }

  setInputAudioTranscription(enabled) {
    console.log("setting input audio transcription: ", enabled);
    this.inputAudioTranscription = enabled;
  }

  setOutputAudioTranscription(enabled) {
    console.log("setting output audio transcription: ", enabled);
    this.outputAudioTranscription = enabled;
  }

  setEnableFunctionCalls(enabled) {
    console.log("setting enable function calls: ", enabled);
    this.enableFunctionCalls = enabled;
  }

  addFunction(newFunction) {
    this.functions.push(newFunction);
    this.functionsMap[newFunction.name] = newFunction;
    console.log("added function: ", newFunction);
  }

  async callFunction(functionName, parameters) {
    const functionToCall = this.functionsMap[functionName];
    return await functionToCall.runFunction(parameters);
  }

  connect() {
    this.setupWebSocketToService();
  }

  disconnect() {
    if (this.webSocket) {
      this.webSocket.close();
      this.connected = false;
    }
  }

  sendMessage(message) {
    console.log("🟩 Sending message: ", message);
    if (this.webSocket && this.webSocket.readyState === WebSocket.OPEN) {
      this.webSocket.send(JSON.stringify(message));
    }
  }

  async onReceiveMessage(messageEvent) {
    console.log("Message received: ", messageEvent);
    let data = messageEvent.data;
    if (data instanceof Blob) {
      try {
        data = await data.text();
      } catch (e) {
        console.error("Error reading Blob as text:", e);
        return;
      }
    }

    if (typeof data !== "string") return;

    try {
      const messageData = JSON.parse(data);
      const message = new MultimodalLiveResponseMessage(messageData);
      this.onReceiveResponse(message);
    } catch (e) {
      console.log("Skipping non-JSON message or parse error:", e);
    }
  }

  setupWebSocketToService() {
    console.log("connecting: ", this.proxyUrl);

    this.webSocket = new WebSocket(this.proxyUrl);

    this.webSocket.onclose = (event) => {
      console.log("websocket closed: ", event);
      this.connected = false;
      this.onErrorMessage("Connection closed");
    };

    this.webSocket.onerror = (event) => {
      console.log("websocket error: ", event);
      this.connected = false;
      this.onErrorMessage("Connection error");
    };

    this.webSocket.onopen = (event) => {
      console.log("websocket open: ", event);
      this.connected = true;
      this.totalBytesSent = 0;
      this.sendInitialSetupMessages();
      this.onConnectionStarted();
    };

    this.webSocket.onmessage = this.onReceiveMessage.bind(this);
  }

  getFunctionDefinitions() {
    console.log("🛠️ getFunctionDefinitions called");
    const tools = [];

    for (let index = 0; index < this.functions.length; index++) {
      const func = this.functions[index];
      tools.push(func.getDefinition());
    }
    return tools;
  }

  sendInitialSetupMessages() {
    const serviceSetupMessage = {
      service_url: this.serviceUrl,
    };
    this.sendMessage(serviceSetupMessage);

    // For Vertex AI Gemini Live API - use snake_case and full resource path
    const sessionSetupMessage = {
      setup: {
        model: `projects/${this.projectId}/locations/${this.location}/publishers/google/models/${this.model}`,
        generation_config: {
          response_modalities: this.responseModalities,
          temperature: this.temperature,
          speech_config: {
            voice_config: {
              prebuilt_voice_config: {
                voice_name: this.voiceName,
              },
            },
          },
        },
        system_instruction: { parts: [{ text: this.systemInstructions }] },
      },
    };

    // Add optional fields only if needed
    if (this.inputAudioTranscription) {
      sessionSetupMessage.setup.input_audio_transcription = {};
    }
    if (this.outputAudioTranscription) {
      sessionSetupMessage.setup.output_audio_transcription = {};
    }

    if (this.enableAffectiveDialog) {
      if (!sessionSetupMessage.setup.generation_config.system_instruction) {
        sessionSetupMessage.setup.system_instruction = { parts: [] };
      }
    }

    // Include tool definitions if any functions are registered
    if (this.functions.length > 0) {
      sessionSetupMessage.setup.tools = [
        { function_declarations: this.getFunctionDefinitions() }
      ];
    }

    // Include realtime input config (VAD settings)
    sessionSetupMessage.setup.realtime_input_config = {
      automatic_activity_detection: { ...this.automaticActivityDetection },
    };
    if (this.activityHandling && this.activityHandling !== "ACTIVITY_HANDLING_UNSPECIFIED") {
      sessionSetupMessage.setup.realtime_input_config.activity_handling = this.activityHandling;
    }

    // Store the setup message for later access
    this.lastSetupMessage = sessionSetupMessage;

    console.log("sessionSetupMessage: ", sessionSetupMessage);
    this.sendMessage(sessionSetupMessage);
  }

  sendTextMessage(text) {
    const textMessage = {
      client_content: {
        turns: [
          {
            role: "user",
            parts: [{ text: text }],
          },
        ],
        turn_complete: true,
      },
    };
    this.sendMessage(textMessage);
  }

  // Inject context without triggering a new model response turn.
  // turn_complete: false tells Gemini "user is still composing input, don't respond yet".
  // The context will be included when the next real user turn (speech/text) completes.
  sendContextMessage(text) {
    const message = {
      client_content: {
        turns: [{ role: "user", parts: [{ text: text }] }],
        turn_complete: false,
      },
    };
    this.sendMessage(message);
  }

  sendToolResponse(toolCallId, name, response) {
    const message = {
      tool_response: {
        function_responses: [
          {
            id: toolCallId,
            name: name,
            response: response,
          },
        ],
      },
    };
    console.log("🔧 Sending tool response:", message);
    this.sendMessage(message);
  }

  sendRealtimeInputMessage(data, mime_type) {
    const message = {
      realtime_input: {
        media_chunks: [
          {
            mime_type: mime_type,
            data: data,
          },
        ],
      },
    };
    this.sendMessage(message);
    this.addToBytesSent(data);
  }

  addToBytesSent(data) {
    const encoder = new TextEncoder();
    const encodedData = encoder.encode(data);
    this.totalBytesSent += encodedData.length;
  }

  getBytesSent() {
    return this.totalBytesSent;
  }

  sendAudioMessage(base64PCM, sampleRate = 16000) {
    const rate = Number.isFinite(sampleRate) ? sampleRate : 16000;
    this.sendRealtimeInputMessage(base64PCM, `audio/pcm;rate=${rate}`);
  }

  async sendImageMessage(base64Image, mime_type = "image/jpeg") {
    this.sendRealtimeInputMessage(base64Image, mime_type);
  }
}

console.log("loaded geminiLiveApi.js");
