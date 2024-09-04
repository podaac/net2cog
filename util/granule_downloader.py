import os
import earthaccess

def download_granule(concept_id):
    granules = earthaccess.granule_query().concept_id(concept_id).get(1)
    files = earthaccess.download(granules,"data")
    return files

def main():
    concept_id = input("Enter the concept-id: ")
    earthaccess.login(persist=True)
    download_granule(concept_id)

if __name__ == "__main__":
    main()
