#!/usr/bin/env bash
# Switch a user's PIAG "lens" for the governance demo:  lens_switch.sh <profile> <email> full|rooftop_R03
set -euo pipefail
P="$1"; EMAIL="$2"; LENS="$3"
uid=$(databricks users list --filter "userName eq '$EMAIL'" -p "$P" -o json | jq -r '.[0].id')
member() {  # member add|remove <group>
  local gid op="$1"
  gid=$(databricks groups list --filter "displayName eq '$2'" -p "$P" -o json | jq -r '.[0].id')
  if [ "$op" = add ]; then
    body="{\"schemas\":[\"urn:ietf:params:scim:api:messages:2.0:PatchOp\"],\"Operations\":[{\"op\":\"add\",\"path\":\"members\",\"value\":[{\"value\":\"$uid\"}]}]}"
  else
    body="{\"schemas\":[\"urn:ietf:params:scim:api:messages:2.0:PatchOp\"],\"Operations\":[{\"op\":\"remove\",\"path\":\"members[value eq \\\"$uid\\\"]\"}]}"
  fi
  databricks groups patch "$gid" -p "$P" --json "$body" >/dev/null && echo "$op $EMAIL -> $2"
}
case "$LENS" in
  full)        for g in piag_margin_viewers piag_crm_admins piag_group_leadership; do member add "$g"; done
               member remove piag_rooftop_R03 ;;
  rooftop_R03) for g in piag_margin_viewers piag_crm_admins piag_group_leadership; do member remove "$g"; done
               member add piag_rooftop_R03 ;;
  *) echo "unknown lens $LENS"; exit 2 ;;
esac
