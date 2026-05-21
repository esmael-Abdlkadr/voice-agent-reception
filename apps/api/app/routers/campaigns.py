import csv
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, status

from app.models import Campaign, CampaignCreate, CampaignCsvImport, CampaignUpdate, Contact
from app.services import agent_service, auth_service, store

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("")
def list_campaigns() -> list[Campaign]:
    return list(store.campaigns.values())


@router.post("", status_code=status.HTTP_201_CREATED)
def create_campaign(payload: CampaignCreate, _user=Depends(auth_service.require_roles("platform_admin", "campaign_operator"))) -> Campaign:
    campaign = Campaign(id=store.next_id("campaign"), status="draft", **payload.model_dump())
    store.campaigns[campaign.id] = campaign
    return campaign


@router.get("/{campaign_id}")
def get_campaign(campaign_id: str) -> Campaign:
    if campaign_id not in store.campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return store.campaigns[campaign_id]


@router.patch("/{campaign_id}")
def update_campaign(campaign_id: str, payload: CampaignUpdate, _user=Depends(auth_service.require_roles("platform_admin", "campaign_operator"))) -> Campaign:
    if campaign_id not in store.campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    campaign = store.campaigns[campaign_id].model_copy(update=payload.model_dump(exclude_unset=True))
    store.campaigns[campaign.id] = campaign
    return campaign


@router.post("/{campaign_id}/start-simulation")
def start_simulation(campaign_id: str, _user=Depends(auth_service.require_roles("platform_admin", "campaign_operator"))) -> dict:
    if campaign_id not in store.campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return agent_service.simulate_campaign(campaign_id)


@router.post("/{campaign_id}/import-csv")
def import_csv(campaign_id: str, payload: CampaignCsvImport, _user=Depends(auth_service.require_roles("platform_admin", "campaign_operator"))) -> dict[str, int | str]:
    if campaign_id not in store.campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    reader = csv.DictReader(StringIO(payload.csv_content))
    imported = 0
    for row in reader:
        name = (row.get("name") or "").strip()
        if not name:
            continue
        contact = Contact(
            id=store.next_id("contact"),
            name=name,
            phone=(row.get("phone") or "").strip(),
            email=(row.get("email") or "").strip(),
            company=(row.get("company") or "BrightCare Dental").strip(),
            source=f"campaign:{campaign_id}",
        )
        store.contacts[contact.id] = contact
        imported += 1
    return {"campaign_id": campaign_id, "imported": imported}
