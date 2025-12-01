# Label Studio Auto Project Setup

This project automatically configures a Label Studio environment using Docker Compose.
It includes a bootstrap process that creates the project, loads the label configuration,
and imports images from an external directory.

## PREREQUISITES
- Docker Desktop (Windows/macOS) or Docker Engine + Compose (Linux)
- Access to the local directory where your images are stored
- Permission to share directories with Docker

## PROJECT STRUCTURE

labelstudio_autoproject/
├── docker-compose.yml
├── .env
├── bootstrap/
│   ├── bootstrap.sh
│   └── label_config.xml
└── mydata/  (persistent Label Studio internal data)

## CONFIGURATION

### 1. Choose the external image directory
   Edit the `.env` file and set the absolute path to your local image directory:

   HOST_REPOSITORY_PATH=/Users/ricardo/Projects/pampas_repository

   On Windows, use this format:
   HOST_REPOSITORY_PATH=C:/Users/Ricardo/Documents/pampas_repository

   On macOS, make sure the directory is shared in:
   Docker Desktop → Settings → Resources → File Sharing

### 2. Configure user and project details
   In the same `.env` file, set the following variables:

   PUBLIC_URL=http://localhost:8080
   LABEL_STUDIO_USERNAME=admin@admin.com
   LABEL_STUDIO_PASSWORD=admin
   LABEL_STUDIO_USER_TOKEN=admin123

   PROJECT_TITLE=Pampas labeling
   PROJECT_DESC=Project for Cortaderia selloana image annotation

## HOW TO RUN

### 1. Start the environment
   From the project root, run:
   **docker compose up**

   This starts Label Studio and automatically runs the bootstrap process
   after the service is ready. The bootstrap will:
   - Create the project (if it doesn’t exist)
   - Apply the label configuration (label_config.xml)
   - Link the external image directory
   - Import and sync all images as labeling tasks

### 2. Access the Label Studio interface
   Once started, open your browser at:
   **http://localhost:8080**

   Login with the credentials specified in the `.env` file.

## IF IMAGES ARE MISSING

If you add new images to your external directory and they do not appear in Label Studio,
rerun the bootstrap to re-sync them:

**docker compose run --rm bootstrap**

This will import any missing images without recreating the project.

## QUICK REFERENCE

Start Label Studio and bootstrap automatically:
    **docker compose up**

Re-import missing or new images:
    **docker compose run --rm bootstrap**

Access Label Studio:
    **http://localhost:8080**

## NOTES

- Make sure HOST_REPOSITORY_PATH points to a valid folder with images.
- The folder is mounted inside the container at:
    /label-studio/files/pampas_repository
- You can safely rerun the bootstrap multiple times; it will not duplicate the project.
- Label Studio data (database, uploads, and configurations) is persisted in ./mydata
