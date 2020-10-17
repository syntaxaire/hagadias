import io
from typing import List
from PIL import Image, ImageSequence
from hagadias.qudtile import QudTile
from hagadias.tileanimator_creategif import save_transparent_gif


class TileAnimator:

    def __init__(self, qud_object):
        """Create a new TileAnimator for the specified QudObject.

        TileAnimator can create a GIF for the QudObject if it qualifies for GIF rendering. The creation
        of a GIF is deferred until the .gif property is accessed. For this reason, you can inexpensively
        instantiate a TileAnimator simply to check the .has_gif property for a particular QudObject."""
        self.qud_object = qud_object
        self._gif_image = None

    @property
    def is_valid(self) -> bool:
        """Basic validation check for this TileAnimator's QudObject. True if the object has a valid tile image."""
        if not self.qud_object.has_tile():
            return False
        if self.qud_object.tile.hasproblems:
            return False
        return True

    @property
    def has_gif(self) -> bool:
        """Whether this TileAnimator's QudObject qualifies for GIF rendering."""
        if self.is_valid:
            if self.qud_object.part_AnimatedMaterialLuminous is not None:
                return True
        return False

    @property
    def gif(self) -> Image:
        """Selects an animation algorithm and applies it. This results in the creation of the GIF image,
        a PIL Image object, which is cached in the _gif_image attribute of this class.

        Note that a PIL Image object is really only a single frame of the GIF. PIL exposes an iterator
        that you can use to walk the GIF frames if you need to (ImageSequence.Iterator). If you want to
        save this GIF to a file or bytestream, you should call GifHelper.save() to ensure that all
        frames and animation delays are properly preserved."""
        if not self.is_valid:
            return None
        if self._gif_image is None:
            if self.qud_object.part_AnimatedMaterialLuminous is not None:
                self.apply_animated_material_luminous()
        return self._gif_image

    def apply_animated_material_luminous(self) -> None:
        """Renders a GIF loosely based on the behavior of the AnimatedMaterialLuminous part."""
        tile = self.qud_object.tile
        frame1and2 = QudTile(tile.filename, '&Y', None, 'C', tile.qudname, tile.raw_transparent)
        frame3 = QudTile(tile.filename, '&C', None, 'C', tile.qudname, tile.raw_transparent)
        self._make_gif([frame1and2, frame3], [40, 20])

    def _make_gif(self, qud_tiles: List[QudTile], durations: List[int]) -> Image:
        """Performs the actual GIF Image creation. Resizes the supplied array of QudTile frames, and appends
        them together as a GIF Image with the specified frame durations (in milliseconds).

        Args:
            qud_tiles: The list of QudTile objects that compose this GIF animation
            durations: The list of durations for each frame in the GIF animation. You should specify durations as
                       milliseconds, but note that they actually only have one tenth of that resolution, because GIF
                       images work on a 100-tick-per-second model. For example, 50 will be internally converted to 5
        """
        frame = qud_tiles[0].get_big_image()
        next_frames: List[Image] = []
        for img in qud_tiles[1:]:
            next_frames.append(img.get_big_image())
        gif_b = io.BytesIO()

        # The following SHOULD work, but there's a bug with the PIL library when creating a new GIF that includes
        # transparency, which causes the GIF to have a black background, among other problems. This doesn't seem to
        # affect subsequent saves after creation, so you can use Image.save() or GifHelper.save() elsewhere in the
        # code to save this GIF instance. For example, we save the GIF in MainWindow.save_selected_tile().
        #   frame.save(gif_b,
        #              format='GIF',
        #              save_all=True,
        #              append_images=next_frames,
        #              transparency=transparency_palette_index,
        #              duration=durations,
        #              loop=0)

        # Workaround code for transparent GIF creation:
        save_transparent_gif([frame] + next_frames, durations, gif_b)

        gif_b.seek(0)
        self._gif_image = Image.open(gif_b)


class GifHelper:

    @staticmethod
    def save(gif_image: Image, save_target):
        """Saves an existing GIF PIL Image object, ensuring that frames and animation delays are properly preserved.

        Args:
            gif_image: A GIF PIL Image object
            save_target: A filename (string), pathlib.Path object or file object. (This parameter corresponds
                         and is passed to the PIL.Image.save() method.)
        """
        durations = []
        for frame in ImageSequence.Iterator(gif_image):
            durations.append(frame.info['duration'])
        gif_image.save(save_target, format='GIF', save_all=True, duration=durations, loop=0)
