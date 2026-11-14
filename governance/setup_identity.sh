#!/usr/bin/env bash
# Idempotent: create the PIAG security groups and the governed tags that drive the ABAC policies.
# Usage: governance/setup_identity.sh <profile> [member-email ...]
#   member emails are added to the four "exception" groups (margin viewers, CRM admins, group
#   leadership, pricing managers) so the builder/pipeline owner sees real values.
set -euo pipefail
P="${1:-DEFAULT}"; shift || true
PIAG_GROUPS=(  # NB: not "GROUPS" - that is a reserved bash variable
  piag_margin_viewers piag_crm_admins piag_group_leadership piag_pricing_managers piag_sales_analysts
        piag_rooftop_R01 piag_rooftop_R02 piag_rooftop_R03 piag_rooftop_R04 piag_rooftop_R05 piag_rooftop_R06)
existing=$(databricks groups list -p "$P" -o json | jq -r '.[].displayName')
for g in "${PIAG_GROUPS[@]}"; do
  if ! grep -qx "$g" <<<"$existing"; then
    databricks groups create --display-name "$g" -p "$P" >/dev/null && echo "created group $g"
  fi
done

# governed tags (tag policies): piag_sensitivity in {financial, pii}; piag_scope in {rooftop}
for spec in 'piag_sensitivity|financial,pii|PIAG data sensitivity class: financial (unit cost, gross) or pii (customer contact details)' \
            'piag_scope|rooftop|PIAG row-scope key: the column identifies the owning rooftop (dealership)'; do
  IFS='|' read -r key vals desc <<<"$spec"
  if ! databricks tag-policies get-tag-policy "$key" -p "$P" >/dev/null 2>&1; then
    json=$(jq -nc --arg k "$key" --arg d "$desc" --arg v "$vals" \
      '{tag_key:$k, description:$d, values:($v|split(",")|map({name:.}))}')
    databricks tag-policies create-tag-policy --json "$json" -p "$P" >/dev/null && echo "created governed tag $key"
  fi
done

add_member() {  # add_member <group> <scim-id>
  local gid
  gid=$(databricks groups list --filter "displayName eq '$1'" -p "$P" -o json | jq -r '.[0].id')
  databricks groups patch "$gid" -p "$P" --json \
    "{\"schemas\":[\"urn:ietf:params:scim:api:messages:2.0:PatchOp\"],\"Operations\":[{\"op\":\"add\",\"path\":\"members\",\"value\":[{\"value\":\"$2\"}]}]}" >/dev/null
  echo "added $2 to $1"
}
for email in "$@"; do
  uid=$(databricks users list --filter "userName eq '$email'" -p "$P" -o json | jq -r '.[0].id')
  for g in piag_margin_viewers piag_crm_admins piag_group_leadership piag_pricing_managers; do add_member "$g" "$uid"; done
done
