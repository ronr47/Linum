use url::Url;

pub struct AgentContextFirewall {
    blocked_params: Vec<&'static str>,
    suspicious_patterns: Vec<&'static str>,
}

impl AgentContextFirewall {
    pub fn new() -> Self {
        Self {
            blocked_params: vec!["autorun", "execute", "eval", "system_override"],
            suspicious_patterns: vec![
                "ignore previous instructions",
                "disregard all prior rules",
                "exfiltrate data to",
                "encode results into url",
            ],
        }
    }

    pub fn inspect_and_sanitize_url(&self, raw_url: &str) -> Result<String, &'static str> {
        let mut parsed_url = Url::parse(raw_url).map_err(|_| "INVALID_URL")?;
        
        // Call into_owned() first to get owned (String, String) pairs
        let pairs: Vec<(String, String)> = parsed_url
            .query_pairs()
            .into_owned()
            .filter(|(k, _)| {
                let key_lower = k.to_lowercase();
                !self.blocked_params.contains(&key_lower.as_str())
            })
            .collect();

        parsed_url.set_query(None);
        if !pairs.is_empty() {
            let mut q = url::form_urlencoded::Serializer::new(String::new());
            for (k, v) in pairs { 
                q.append_pair(&k, &v); 
            }
            parsed_url.set_query(Some(&q.finish()));
        }
        Ok(parsed_url.to_string())
    }

    pub fn scan_payload_text(&self, payload: &str) -> bool {
        let norm = payload.to_lowercase();
        !self.suspicious_patterns.iter().any(|p| norm.contains(p))
    }
}
