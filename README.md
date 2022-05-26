# testing-rts-python
Mock rts upload shenanigans 

# Requirements
- hunt-sdk-python: https://github.com/Infocyte/hunt-sdk-python.git
- process and account ndjson files from offline scan.
    - set file paths in account_payload, and process_payload variables


hunt-sdk-python needs two environment variables:
- "HUNT_URL", e.g https://testhomer19.infocyte.com
- "HUNT_TOKEN", generated in UI for test instance (admin > Users and Tokens > API Tokens)


Currently set to generate 50 mock agents and rts upload
- variable name is agent_count