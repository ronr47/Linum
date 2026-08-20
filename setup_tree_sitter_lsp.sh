#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(pwd)"
mkdir -p "${ROOT_DIR}/tree-sitter-linum" \
         "${ROOT_DIR}/src/linum_lsp/src"

# Tree-sitter Grammar Definition
cat << 'JS_EOF' > "${ROOT_DIR}/tree-sitter-linum/grammar.js"
module.exports = grammar({
  name: 'linum',

  rules: {
    source_file: $ => repeat($._statement),

    _statement: $ => choice(
      $.let_binding,
      $.return_statement,
      $.block
    ),

    let_binding: $ => seq(
      'let',
      field('name', $.identifier),
      ':',
      field('type', $.type_specifier),
      '=',
      field('value', $._expression),
      ';'
    ),

    return_statement: $ => seq('return', $._expression, ';'),

    block: $ => seq('{', repeat($._statement), '}'),

    _expression: $ => choice(
      $.identifier,
      $.literal_register,
      $.binary_op
    ),

    binary_op: $ => prec.left(1, seq(
      $._expression,
      choice('+', '-', '*', '/'),
      $._expression
    )),

    literal_register: $ => seq('%', choice('val_42', 'uninit_stub', /[a-zA-Z0-9_]+/)),
    type_specifier: $ => choice('ptr', 'COPY', 'i32', 'f64'),
    identifier: $ => /[a-zA-Z_][a-zA-Z0-9_]*/,
  }
});
JS_EOF

# Lightweight LSP Skeleton with Tower-LSP
cat << 'LSP_CARGO_EOF' > "${ROOT_DIR}/src/linum_lsp/Cargo.toml"
[package]
name = "linum_lsp"
version = "0.1.0"
edition = "2021"

[dependencies]
tokio = { version = "1.36", features = ["full"] }
tower-lsp = "0.20"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
LSP_CARGO_EOF

cat << 'LSP_SRC_EOF' > "${ROOT_DIR}/src/linum_lsp/src/main.rs"
use tower_lsp::jsonrpc::Result;
use tower_lsp::lsp_types::*;
use tower_lsp::{Client, LanguageServer, LspService, Server};

#[derive(Debug)]
struct LinumBackend {
    client: Client,
}

#[tower_lsp::async_trait]
impl LanguageServer for LinumBackend {
    async fn initialize(&self, _: InitializeParams) -> Result<InitializeResult> {
        Ok(InitializeResult {
            capabilities: ServerCapabilities {
                hover_provider: Some(HoverProviderCapability::Simple(true)),
                completion_provider: Some(CompletionOptions {
                    resolve_provider: Some(false),
                    trigger_characters: Some(vec!["%".to_string(), ":".to_string()]),
                    ..Default::default()
                }),
                ..Default::default()
            },
            ..Default::default()
        })
    }

    async fn shutdown(&self) -> Result<()> {
        Ok(())
    }

    async fn hover(&self, _: HoverParams) -> Result<Option<Hover>> {
        Ok(Some(Hover {
            contents: HoverContents::Scalar(MarkedString::String(
                "⚡ Linum 2050 Quantum Lifetime: Pure Affine Variable".to_string(),
            )),
            range: None,
        }))
    }
}

#[tokio::main]
async fn main() {
    let stdin = tokio::io::stdin();
    let stdout = tokio::io::stdout();
    let (service, socket) = LspService::new(|client| LinumBackend { client });
    Server::new(stdin, stdout, socket).serve(service).await;
}
LSP_SRC_EOF

echo "      [✔] Tree-sitter grammar and Tower-LSP backend deployed."
