import logging

from backend.agent.state import State
from backend.config import MAX_MODIFICATION_COUNT

logger = logging.getLogger(__name__)


def modify_loop_node(state: State) -> dict:
    """Gate the modify -> regenerate loop on the user's modification opinion.

    The revision request is promoted to the top-level ``modification_opinion``
    state field instead of being appended to a growing message list, so the
    checkpointed state stays bounded no matter how many rounds the user runs.

    This is the single decision point for the loop: the run only goes back to
    regeneration when the user actually left an opinion, and it stops once the
    modification budget is exhausted.
    """
    generation_id = state.get("generation_id")
    opinion = (state.get("modification_opinion") or "").strip()
    round_index = state.get("modification_count", 0)

    if not opinion:
        logger.warning(
            "modify_loop: no modification opinion for generation %s; "
            "ending run after %d modification round(s)",
            generation_id,
            round_index,
        )
        return {"enter_loop": False, "should_end": True, "modification_opinion": ""}

    if round_index >= MAX_MODIFICATION_COUNT:
        logger.warning(
            "modify_loop: modification budget %d exhausted for generation %s; "
            "ending run and keeping draft chapters",
            MAX_MODIFICATION_COUNT,
            generation_id,
        )
        return {"enter_loop": False, "should_end": True, "modification_opinion": ""}

    round_index += 1
    logger.info(
        "modify_loop: starting modification round %d/%d for generation %s "
        "(opinion length=%d)",
        round_index,
        MAX_MODIFICATION_COUNT,
        generation_id,
        len(opinion),
    )
    return {
        "enter_loop": True,
        "should_end": False,
        "modification_count": round_index,
        "modification_opinion": opinion,
    }
