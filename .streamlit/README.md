# Local Development Setup

This directory contains configuration for local development that mimics Railway's environment.

## Setting up secrets.toml

1. **Copy the template**: Copy `secrets.toml.template` to `secrets.toml`
2. **Fill in your values**: Replace the placeholder values with your actual API keys and credentials

## Required Credentials

### GitHub Token
1. Go to GitHub: Settings > Developer settings > Personal access tokens > Tokens (classic)
2. Generate a new token with `repo` permissions
3. Copy the token and paste it as the value for `GITHUB_TOKEN`

### Google Service Account
1. Go to Google Cloud Console: APIs & Services > Credentials
2. Create a new Service Account or use an existing one
3. Download the JSON key file
4. Copy the values from the JSON file to the corresponding fields in `secrets.toml`

## Important Notes

- **Never commit secrets.toml to Git** - it's already in .gitignore
- **Keep your API keys secure** - don't share them or commit them to version control
- **Use different tokens for development and production** - Railway uses environment variables

## Testing

Once you've set up your secrets, you can test the GitHub connection by running:
```bash
streamlit run simple_test.py
```

This will verify that your GitHub token is working and can access the repository. 