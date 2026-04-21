import React from 'react'
import { Modal, ModalHeader, ModalContent } from '@/components/ui/modal'

export default function ApiKeyHelpModal({ open, onClose }) {
  return (
    <Modal open={open} onClose={onClose}>
      <ModalHeader onClose={onClose}>
        Supported Model Providers
      </ModalHeader>
      <ModalContent>
        <div className="space-y-5 text-sm text-neutral-700 dark:text-neutral-300">
          <div>
            <h3 className="font-semibold text-neutral-800 dark:text-neutral-100 mb-1">Anthropic — API Key</h3>
            <ol className="list-decimal list-inside space-y-1 text-neutral-600 dark:text-neutral-400">
              <li>Go to <a href="https://console.anthropic.com/" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 underline">console.anthropic.com</a></li>
              <li>Create an account or sign in</li>
              <li>Navigate to the API Keys section</li>
              <li>Create a new API key (starts with <code className="bg-neutral-100 dark:bg-neutral-700 px-1 rounded">sk-ant-</code>)</li>
            </ol>
            <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-500">Select <strong>Anthropic (API Key)</strong> as the provider when saving.</p>
          </div>

          <div>
            <h3 className="font-semibold text-neutral-800 dark:text-neutral-100 mb-1">Anthropic — Claude OAuth</h3>
            <ol className="list-decimal list-inside space-y-1 text-neutral-600 dark:text-neutral-400">
              <li>Requires an active Claude Pro or Max subscription</li>
              <li>Install <a href="https://code.claude.com" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 underline">Claude Code</a> if you haven't already</li>
              <li>Run <code className="bg-neutral-100 dark:bg-neutral-700 px-1 rounded">claude setup-token</code> in your terminal</li>
              <li>Follow the prompts to authenticate — this generates an OAuth token (starts with <code className="bg-neutral-100 dark:bg-neutral-700 px-1 rounded">sk-ant-oat-</code>)</li>
              <li>Copy the token and paste it here</li>
            </ol>
            <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-500">Select <strong>Anthropic (OAuth)</strong> as the provider when saving.</p>
          </div>

          <div>
            <h3 className="font-semibold text-neutral-800 dark:text-neutral-100 mb-1">OpenAI — API Key</h3>
            <ol className="list-decimal list-inside space-y-1 text-neutral-600 dark:text-neutral-400">
              <li>Go to <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 underline">platform.openai.com/api-keys</a></li>
              <li>Create an account or sign in (separate from your ChatGPT account)</li>
              <li>Create an organization if you haven't already</li>
              <li>Navigate to API Keys and create a new secret key (starts with <code className="bg-neutral-100 dark:bg-neutral-700 px-1 rounded">sk-proj-</code>)</li>
              <li>Copy it immediately — it is only shown once</li>
            </ol>
            <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-500">Select <strong>OpenAI</strong> as the provider when saving. Requires billing setup on the OpenAI platform.</p>
          </div>

          <div>
            <h3 className="font-semibold text-neutral-800 dark:text-neutral-100 mb-1">OpenAI Codex — ChatGPT Subscription</h3>
            <p className="text-neutral-600 dark:text-neutral-400">Use your ChatGPT Plus or Pro subscription instead of paying per-token API costs. No API key needed.</p>
            <ol className="list-decimal list-inside space-y-1 text-neutral-600 dark:text-neutral-400 mt-1">
              <li>Go to global <strong>Settings</strong> then <strong>Credentials</strong></li>
              <li>Click <strong>Add Credential</strong> and choose <strong>ChatGPT Codex</strong></li>
              <li>The sign-in page opens immediately — sign in with your ChatGPT account</li>
              <li>Once connected, select the ChatGPT Codex credential in your project settings</li>
            </ol>
            <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-500">When using the dashboard remotely, copy the final <code className="bg-neutral-100 dark:bg-neutral-700 px-1 rounded">http://localhost...</code> callback URL from the browser and paste it back into HPC Agent.</p>
          </div>

          <div>
            <h3 className="font-semibold text-neutral-800 dark:text-neutral-100 mb-1">Google (Gemini)</h3>
            <ol className="list-decimal list-inside space-y-1 text-neutral-600 dark:text-neutral-400">
              <li>Go to <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 underline">aistudio.google.com/apikey</a></li>
              <li>Sign in with your Google account and accept the terms</li>
              <li>Click <strong>Create API key</strong> and copy it</li>
            </ol>
            <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-500">Select <strong>Google (Gemini)</strong> as the provider when saving. Free tier available with rate limits.</p>
          </div>

          <div>
            <h3 className="font-semibold text-neutral-800 dark:text-neutral-100 mb-1">MiniMax</h3>
            <ol className="list-decimal list-inside space-y-1 text-neutral-600 dark:text-neutral-400">
              <li>Global: <a href="https://platform.minimax.io/" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 underline">platform.minimax.io</a> — China: <a href="https://platform.minimaxi.com/" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 underline">platform.minimaxi.com</a></li>
              <li>Create an account and sign in</li>
              <li>Navigate to API Keys and create a new key — copy it immediately (shown once)</li>
            </ol>
            <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-500">Select <strong>MiniMax</strong> as the provider when saving. API key and host must match the same region.</p>
          </div>

          <div className="border-t border-neutral-200 dark:border-neutral-700 pt-4">
            <h3 className="font-semibold text-neutral-800 dark:text-neutral-100 mb-1">Tips</h3>
            <ul className="list-disc list-inside space-y-1 text-neutral-600 dark:text-neutral-400">
              <li>You can configure different providers per project</li>
              <li>Projects without a key will fall back to the global key</li>
              <li>Select the correct provider from the dropdown — keys are not auto-detected</li>
            </ul>
          </div>
        </div>
      </ModalContent>
    </Modal>
  )
}
